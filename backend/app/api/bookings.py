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


def _booking_totals(booking: Booking) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = sum(
        (
            sum((line.quantity * line.rate for line in event.line_items), Decimal("0"))
            for event in booking.events
        ),
        Decimal("0"),
    )
    paid = sum((payment.amount for payment in booking.payments), Decimal("0"))
    balance = subtotal - paid
    return subtotal, paid, balance


def _booking_bill_pdf(booking: Booking, company_settings: CompanySettings) -> bytes:
    subtotal, paid, balance = _booking_totals(booking)
    payment_status = "Pending" if balance > 0 else "Done"
    commands: list[str] = []

    _rect(commands, 34, 34, 527, 774, fill="1 1 1", stroke="0.831 0.858 0.902")
    _line(commands, 58, 730, 537, 730, color="0.059 0.353 0.643", width=2.4)
    _rect(commands, 58, 742, 86, 50, fill="0.059 0.353 0.643")
    _text(commands, company_settings.invoice_prefix[:8], 77, 761, size=18, font="F2", color="1 1 1")
    _text(commands, "FINAL BILL", 160, 779, size=8, font="F2", color="0.392 0.455 0.545")
    _text(commands, company_settings.company_name.upper(), 160, 754, size=22, font="F2")
    _text(commands, "Laser, LED, Sharpee and FX lighting supplier", 160, 738, size=9, color="0.392 0.455 0.545")
    _rect(commands, 400, 744, 137, 48, fill="0.969 0.980 0.988", stroke="0.827 0.859 0.902")
    _text(commands, "INVOICE NO.", 418, 776, size=7, font="F2", color="0.392 0.455 0.545")
    _text(commands, f"{company_settings.invoice_prefix}-{booking.booking_no}", 418, 760, size=13, font="F2")
    _text(commands, _date_text(booking.start_date), 418, 748, size=8, color="0.392 0.455 0.545")

    _info_box(commands, 58, 655, 145, "BILL TO", [booking.client.name, booking.client.mobile, booking.client.address or ""])
    _info_box(
        commands,
        224,
        655,
        170,
        "BOOKING",
        [
            booking.title,
            f"{_date_text(booking.start_date)} to {_date_text(booking.end_date)}",
            f"{len(booking.events)} linked event entries",
        ],
    )
    _info_box(commands, 418, 655, 119, "AMOUNT DUE", [_money(balance), f"Status: {payment_status}"], highlight=True)

    y = 610
    for index, event in enumerate(booking.events, start=1):
        visible_lines = list(event.line_items)[:6]
        event_height = 62 + (max(len(visible_lines), 1) * 18) + 22
        if y - event_height < 205:
            _text(commands, "More event details continue in the app preview.", 58, y, size=8, color="0.392 0.455 0.545")
            break

        event_total = sum((line.quantity * line.rate for line in event.line_items), Decimal("0"))
        _rect(commands, 58, y - event_height, 479, event_height, stroke="0.827 0.859 0.902")
        _rect(commands, 58, y - 34, 479, 34, fill="0.961 0.973 0.988", stroke="0.827 0.859 0.902")
        _text(commands, f"EVENT {index}", 74, y - 13, size=7, font="F2", color="0.392 0.455 0.545")
        _text(commands, event.name, 74, y - 27, size=12, font="F2")
        _text(commands, _date_text(event.event_date), 458, y - 13, size=8, font="F2", align="right")
        _text(commands, event.venue or "", 458, y - 27, size=8, color="0.392 0.455 0.545", align="right")

        table_y = y - 52
        _rect(commands, 58, table_y - 16, 479, 16, fill="0.059 0.353 0.643")
        _text(commands, "Material", 72, table_y - 12, size=8, font="F2", color="1 1 1")
        _text(commands, "Qty", 355, table_y - 12, size=8, font="F2", color="1 1 1", align="right")
        _text(commands, "Rate", 440, table_y - 12, size=8, font="F2", color="1 1 1", align="right")
        _text(commands, "Amount", 522, table_y - 12, size=8, font="F2", color="1 1 1", align="right")

        row_y = table_y - 34
        if visible_lines:
            for line in visible_lines:
                _text(commands, line.material_name, 72, row_y, size=8)
                _text(commands, _quantity(line.quantity), 355, row_y, size=8, align="right")
                _text(commands, _money(line.rate), 440, row_y, size=8, align="right")
                _text(commands, _money(line.quantity * line.rate), 522, row_y, size=8, align="right")
                _line(commands, 58, row_y - 7, 537, row_y - 7, color="0.925 0.941 0.961", width=0.6)
                row_y -= 18
        else:
            _text(commands, "No material added yet.", 72, row_y, size=8, color="0.392 0.455 0.545")
            row_y -= 18

        _rect(commands, 58, y - event_height, 479, 20, fill="0.976 0.984 0.992")
        _text(commands, "Event Subtotal", 420, y - event_height + 7, size=8, font="F2", color="0.059 0.353 0.643", align="right")
        _text(commands, _money(event_total), 522, y - event_height + 7, size=8, font="F2", color="0.059 0.353 0.643", align="right")
        y -= event_height + 14

    bottom_y = 78
    _rect(commands, 58, bottom_y, 270, 98, stroke="0.827 0.859 0.902")
    _text(commands, "Payments", 74, bottom_y + 76, size=12, font="F2")
    payment_y = bottom_y + 58
    if booking.payments:
        for payment in list(booking.payments)[:4]:
            _text(commands, _date_text(payment.payment_date), 74, payment_y, size=8, color="0.392 0.455 0.545")
            _text(commands, payment.mode, 160, payment_y, size=8)
            _text(commands, _money(payment.amount), 310, payment_y, size=8, font="F2", align="right")
            payment_y -= 16
    else:
        _text(commands, "No advance payment recorded.", 74, payment_y, size=8, color="0.392 0.455 0.545")

    _rect(commands, 350, bottom_y, 187, 98, fill="0.067 0.094 0.153")
    _text(commands, "Subtotal", 368, bottom_y + 70, size=9, color="0.796 0.835 0.882")
    _text(commands, _money(subtotal), 518, bottom_y + 70, size=9, font="F2", color="1 1 1", align="right")
    _text(commands, "Advance Paid", 368, bottom_y + 48, size=9, color="0.796 0.835 0.882")
    _text(commands, _money(paid), 518, bottom_y + 48, size=9, font="F2", color="1 1 1", align="right")
    _line(commands, 366, bottom_y + 32, 521, bottom_y + 32, color="0.247 0.290 0.357", width=0.8)
    _text(commands, "Balance Due", 368, bottom_y + 16, size=11, color="0.796 0.835 0.882")
    _text(commands, _money(balance), 518, bottom_y + 16, size=11, font="F2", color="1 1 1", align="right")

    _rect(commands, 58, 44, 479, 22, fill="0.933 0.965 0.992", stroke="0.784 0.875 0.953")
    _text(commands, "Thank you for your business.", 74, 52, size=9, font="F2")
    _text(commands, "All materials are billed event-wise and linked under this wedding booking.", 522, 52, size=7, color="0.392 0.455 0.545", align="right")

    stream = "\n".join(commands).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R /F2 6 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
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
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _text(
    commands: list[str],
    value: str,
    x: int | float,
    y: int | float,
    *,
    size: int | float = 10,
    font: str = "F1",
    color: str = "0.067 0.094 0.153",
    align: str = "left",
) -> None:
    text = _clip_text(str(value), 54 if size <= 8 else 36)
    text_width = len(text) * size * 0.48
    draw_x = x - text_width if align == "right" else x
    commands.append(f"{color} rg")
    commands.append(f"BT /{font} {size} Tf {draw_x:.2f} {y:.2f} Td ({_pdf_escape(text)}) Tj ET")


def _rect(
    commands: list[str],
    x: int | float,
    y: int | float,
    width: int | float,
    height: int | float,
    *,
    fill: str | None = None,
    stroke: str | None = None,
) -> None:
    if fill:
        commands.append(f"{fill} rg")
    if stroke:
        commands.append(f"{stroke} RG")
    operator = "B" if fill and stroke else "f" if fill else "S"
    commands.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re {operator}")


def _line(
    commands: list[str],
    x1: int | float,
    y1: int | float,
    x2: int | float,
    y2: int | float,
    *,
    color: str = "0 0 0",
    width: int | float = 1,
) -> None:
    commands.append(f"{color} RG {width} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")


def _info_box(
    commands: list[str],
    x: int,
    y: int,
    width: int,
    label: str,
    values: list[str],
    *,
    highlight: bool = False,
) -> None:
    _line(commands, x, y - 60, x, y, color="0.898 0.929 0.965", width=3)
    _text(commands, label, x + 12, y - 10, size=7, font="F2", color="0.392 0.455 0.545")
    _text(commands, values[0], x + 12, y - 28, size=17 if highlight else 11, font="F2", color="0.059 0.353 0.643" if highlight else "0.067 0.094 0.153")
    for index, value in enumerate(values[1:], start=1):
        _text(commands, value, x + 12, y - 28 - (index * 14), size=8, color="0.392 0.455 0.545")


def _clip_text(value: str, length: int) -> str:
    clean_value = " ".join(str(value or "").split())
    if len(clean_value) <= length:
        return clean_value
    return f"{clean_value[: max(length - 3, 0)]}..."


def _date_text(value) -> str:
    return value.isoformat() if value else ""


def _money(value: Decimal) -> str:
    return f"Rs. {value:,.2f}"


def _quantity(value: Decimal) -> str:
    normalized = value.normalize()
    return f"{normalized:f}"
