from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

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
    return (
        selectinload(Booking.client),
        selectinload(Booking.events).selectinload(BookingEvent.line_items),
        selectinload(Booking.payments),
    )


def normalized_event_name(name: str) -> str:
    return " ".join(name.split()).lower()


def ensure_unique_event_names(event_payloads: list[BookingEventCreate]) -> None:
    seen_event_names: set[str] = set()
    for event_payload in event_payloads:
        event_name = normalized_event_name(event_payload.name)
        if event_name in seen_event_names:
            raise HTTPException(status_code=409, detail="Event already exists for this booking")
        seen_event_names.add(event_name)


@router.get("", response_model=list[BookingRead])
def list_bookings(db: Session = Depends(get_db)) -> list[Booking]:
    statement = select(Booking).options(*booking_options()).order_by(Booking.created_at.desc())
    return list(db.scalars(statement))


@router.get("/{booking_id}", response_model=BookingRead)
def get_booking(booking_id: int, db: Session = Depends(get_db)) -> Booking:
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).options(*booking_options()))
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.post("", response_model=BookingRead, status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)) -> Booking:
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    event_payloads = payload.events
    ensure_unique_event_names(event_payloads)

    booking = Booking(**payload.model_dump(exclude={"events"}))
    for event_payload in event_payloads:
        booking.events.append(_build_event(event_payload))

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return get_booking(booking.id, db)


@router.post("/{booking_id}/events", response_model=BookingRead, status_code=201)
def add_booking_event(
    booking_id: int,
    payload: BookingEventCreate,
    db: Session = Depends(get_db),
) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    new_event_name = normalized_event_name(payload.name)
    duplicate_event = any(
        normalized_event_name(existing_event.name) == new_event_name for existing_event in booking.events
    )
    if duplicate_event:
        raise HTTPException(status_code=409, detail="Event already exists for this booking")

    booking.events.append(_build_event(payload))
    db.commit()
    return get_booking(booking_id, db)


@router.delete("/{booking_id}", status_code=204)
def delete_booking(booking_id: int, db: Session = Depends(get_db)) -> None:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    db.delete(booking)
    db.commit()


@router.delete("/events/{event_id}", response_model=BookingRead)
def delete_booking_event(event_id: int, db: Session = Depends(get_db)) -> Booking:
    event = db.get(BookingEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    booking_id = event.booking_id
    db.delete(event)
    db.commit()
    return get_booking(booking_id, db)


@router.post("/events/{event_id}/line-items", response_model=BookingRead, status_code=201)
def add_event_line_item(
    event_id: int,
    payload: EventLineItemCreate,
    db: Session = Depends(get_db),
) -> Booking:
    event = db.get(BookingEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    event.line_items.append(EventLineItem(**payload.model_dump()))
    db.commit()
    return get_booking(event.booking_id, db)


@router.post("/{booking_id}/payments", response_model=PaymentRead, status_code=201)
def add_payment(
    booking_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
) -> Payment:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    payment = Payment(booking_id=booking_id, **payload.model_dump())
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def _build_event(payload: BookingEventCreate) -> BookingEvent:
    line_payloads = payload.line_items
    event = BookingEvent(**payload.model_dump(exclude={"line_items"}))
    for line_payload in line_payloads:
        event.line_items.append(EventLineItem(**line_payload.model_dump()))
    return event
