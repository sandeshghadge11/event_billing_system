from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, with_loader_criteria

from app.core.database import get_db
from app.models.booking import Booking, BookingEvent, EventLineItem, Payment
from app.models.client import Client
from app.schemas.booking import (
    BookingCreate,
    BookingEventCreate,
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


def _build_event(payload: BookingEventCreate) -> BookingEvent:
    """Convert a nested event request into SQLAlchemy event and line-item rows."""

    line_payloads = payload.line_items
    event = BookingEvent(**payload.model_dump(exclude={"line_items"}))
    for line_payload in line_payloads:
        event.line_items.append(EventLineItem(**line_payload.model_dump()))
    return event
