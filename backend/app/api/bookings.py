import smtplib
from decimal import Decimal
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, with_loader_criteria

from app.core.config import settings as app_settings
from app.core.database import get_db
from app.models.booking import Booking, BookingEvent, EventLineItem, Payment
from app.models.client import Client
from app.models.company_settings import CompanySettings
from app.schemas.booking import (
    BookingCreate,
    BookingEventCreate,
    BookingMailRequest,
    BookingRead,
    EventLineItemCreate,
    PaymentCreate,
    PaymentRead,
)

router = APIRouter()


def booking_options():
    """Eager-load nested data needed by BookingRead responses."""

    # These options tell SQLAlchemy to fetch client, events, line items, and
    # payments together. That keeps response serialization from making many
    # small database calls later.
    return (
        selectinload(Booking.client),
        selectinload(Booking.events).selectinload(BookingEvent.line_items),
        selectinload(Booking.payments),
        with_loader_criteria(BookingEvent, BookingEvent.is_active.is_(True)),
    )


def normalized_event_name(name: str) -> str:
    """Normalize event names for duplicate checks inside one booking."""

    return " ".join(name.split()).lower()


def ensure_unique_event_names(event_payloads: list[BookingEventCreate]) -> None:
    """Reject duplicate event names before creating a booking with events."""

    seen_event_names: set[str] = set()
    for event_payload in event_payloads:
        event_name = normalized_event_name(event_payload.name)
        if not event_name:
            raise HTTPException(status_code=400, detail="Event name is required")
        if event_name in seen_event_names:
            raise HTTPException(status_code=409, detail="Event already exists for this booking")
        seen_event_names.add(event_name)


@router.get("", response_model=list[BookingRead])
def list_bookings(db: Session = Depends(get_db)) -> list[Booking]:
    """Return every booking with nested client, events, line items, and payments."""

    statement = (
        select(Booking)
        .where(Booking.is_active.is_(True))
        .options(*booking_options())
        .order_by(Booking.created_at.desc())
    )
    return list(db.scalars(statement))


@router.get("/{booking_id}", response_model=BookingRead)
def get_booking(booking_id: int, db: Session = Depends(get_db)) -> Booking:
    """Return one booking by id, including all nested billing details."""

    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id, Booking.is_active.is_(True))
        .options(*booking_options())
    )
    if booking is None or not booking.is_active:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.post("", response_model=BookingRead, status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)) -> Booking:
    """Create a booking for an existing client, optionally with events."""

    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Booking name is required")

    # The frontend creates a client first, then calls this route with client_id.
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    event_payloads = payload.events
    ensure_unique_event_names(event_payloads)

    # Build the parent Booking row from request fields, then attach child events.
    booking = Booking(**payload.model_dump(exclude={"events"}))
    for event_payload in event_payloads:
        booking.events.append(_build_event(event_payload))

    db.add(booking)
    db.commit()
    db.refresh(booking)
    # Re-read with booking_options() so the API response contains nested objects.
    return get_booking(booking.id, db)


@router.post("/{booking_id}/events", response_model=BookingRead, status_code=201)
def add_booking_event(
    booking_id: int,
    payload: BookingEventCreate,
    db: Session = Depends(get_db),
) -> Booking:
    """Attach one new event to an existing booking."""

    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Booking events are unique by normalized name inside the same booking.
    new_event_name = normalized_event_name(payload.name)
    if not new_event_name:
        raise HTTPException(status_code=400, detail="Event name is required")

    existing_events = db.scalars(
        select(BookingEvent).where(
            BookingEvent.booking_id == booking_id,
            BookingEvent.is_active.is_(True),
        )
    )
    duplicate_event = any(
        normalized_event_name(existing_event.name) == new_event_name for existing_event in existing_events
    )
    if duplicate_event:
        raise HTTPException(status_code=409, detail="Event already exists for this booking")

    booking.events.append(_build_event(payload))
    db.commit()
    return get_booking(booking_id, db)


@router.delete("/{booking_id}", status_code=204)
def delete_booking(booking_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a booking and its child events, line items, and payments."""

    booking = db.get(Booking, booking_id)
    if booking is None or not booking.is_active:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.is_active = False
    booking.status = "Inactive"
    db.commit()


@router.delete("/events/{event_id}", response_model=BookingRead)
def delete_booking_event(event_id: int, db: Session = Depends(get_db)) -> Booking:
    """Delete one event and return the updated parent booking."""

    event = db.get(BookingEvent, event_id)
    if event is None or not event.is_active:
        raise HTTPException(status_code=404, detail="Event not found")

    # Store the parent id before deletion so we can reload the booking afterward.
    booking_id = event.booking_id
    event.is_active = False
    event.status = "Inactive"
    db.commit()
    return get_booking(booking_id, db)


@router.post("/events/{event_id}/line-items", response_model=BookingRead, status_code=201)
def add_event_line_item(
    event_id: int,
    payload: EventLineItemCreate,
    db: Session = Depends(get_db),
) -> Booking:
    """Add one material/rate/quantity row to an event and return the booking."""

    event = db.get(BookingEvent, event_id)
    if event is None or not event.is_active:
        raise HTTPException(status_code=404, detail="Event not found")

    if not payload.material_name.strip():
        raise HTTPException(status_code=400, detail="Material name is required")
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
    if payload.rate < 0:
        raise HTTPException(status_code=400, detail="Rate cannot be negative")

    # The EventLineItem belongs to the event through the relationship list.
    event.line_items.append(EventLineItem(**payload.model_dump()))
    db.commit()
    return get_booking(event.booking_id, db)


@router.post("/{booking_id}/payments", response_model=PaymentRead, status_code=201)
def add_payment(
    booking_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
) -> Payment:
    """Record an advance/final payment against a booking."""

    booking = db.get(Booking, booking_id)
    if booking is None or not booking.is_active:
        raise HTTPException(status_code=404, detail="Booking not found")

    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than 0")

    # Payment has its own endpoint because it is an independent transaction
    # against the booking balance.
    payment = Payment(booking_id=booking_id, **payload.model_dump())
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/{booking_id}/send-mail")
def send_booking_bill(
    booking_id: int,
    payload: BookingMailRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Send the saved booking bill as a PDF attachment."""

    company_settings = _get_company_settings(db)
    sender_email = (company_settings.send_mail or app_settings.send_mail).strip()
    receiver_email = (company_settings.recv_mail or app_settings.recv_mail).strip()
    if "@" not in sender_email:
        raise HTTPException(status_code=400, detail="Sender email is required")
    if "@" not in receiver_email:
        raise HTTPException(status_code=400, detail="Receiver email is required")
    if not app_settings.smtp_app_password:
        raise HTTPException(status_code=500, detail="SMTP app password is not configured")

    booking = get_booking(booking_id, db)
    message = EmailMessage()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = f"Bill for {booking.title} - {company_settings.invoice_prefix}-{booking.booking_no}"
    message.set_content("Please find the attached bill PDF.")
    message.add_attachment(
        _booking_bill_pdf(booking, company_settings),
        maintype="application",
        subtype="pdf",
        filename=f"{company_settings.invoice_prefix}-{booking.booking_no}.pdf",
    )

    try:
        with smtplib.SMTP(app_settings.smtp_host, app_settings.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(sender_email, app_settings.smtp_app_password)
            smtp.send_message(message)
    except smtplib.SMTPException as error:
        raise HTTPException(status_code=502, detail=f"Could not send bill email: {error}") from error

    return {"message": "Bill email sent"}


def _build_event(payload: BookingEventCreate) -> BookingEvent:
    """Convert a nested event request into SQLAlchemy event and line-item rows."""

    line_payloads = payload.line_items
    event = BookingEvent(**payload.model_dump(exclude={"line_items"}))
    for line_payload in line_payloads:
        event.line_items.append(EventLineItem(**line_payload.model_dump()))
    return event


def _get_company_settings(db: Session) -> CompanySettings:
    company_settings = db.get(CompanySettings, 1)
    if company_settings is not None:
        return company_settings

    company_settings = CompanySettings(id=1)
    db.add(company_settings)
    db.commit()
    db.refresh(company_settings)
    return company_settings


def _booking_bill_lines(booking: Booking, company_settings: CompanySettings) -> list[str]:
    subtotal = sum(
        (
            sum((line.quantity * line.rate for line in event.line_items), Decimal("0"))
            for event in booking.events
        ),
        Decimal("0"),
    )
    paid = sum((payment.amount for payment in booking.payments), Decimal("0"))
    balance = subtotal - paid
    lines = [
        company_settings.company_name,
        f"Invoice No: {company_settings.invoice_prefix}-{booking.booking_no}",
        f"Booking: {booking.title}",
        f"Client: {booking.client.name}",
        f"Mobile: {booking.client.mobile}",
        f"Company Mobile: {company_settings.owner_mobile}",
        "",
        "Events",
    ]

    for event in booking.events:
        event_total = sum((line.quantity * line.rate for line in event.line_items), Decimal("0"))
        lines.append(f"- {event.name} | {event.event_date or ''} | {event.venue or ''} | {event_total}")
        for line in event.line_items:
            lines.append(f"  {line.material_name}: {line.quantity} x {line.rate} = {line.quantity * line.rate}")

    lines.extend(
        [
            "",
            f"Subtotal: {subtotal}",
            f"Advance Paid: {paid}",
            f"Balance Due: {balance}",
            "",
            "Thank you for your business.",
        ]
    )
    return lines


def _booking_bill_pdf(booking: Booking, company_settings: CompanySettings) -> bytes:
    lines = _booking_bill_lines(booking, company_settings)
    content_lines = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    for index, line in enumerate(lines[:48]):
        if index:
            content_lines.append("T*")
        content_lines.append(f"({_pdf_escape(line)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_number} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
