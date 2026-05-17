from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.event_type import EventType
from app.schemas.event_type import EventTypeCreate, EventTypeRead

router = APIRouter()


def normalize_event_name(name: str) -> str:
    """Trim repeated spaces and keep a consistent display format for events."""

    clean_name = " ".join(name.split())
    if not clean_name:
        return clean_name
    return clean_name[0].upper() + clean_name[1:]


@router.get("", response_model=list[EventTypeRead])
def list_event_types(db: Session = Depends(get_db)) -> list[EventType]:
    """Return configured event names such as Sangeet, Haldi, and Reception."""

    return list(db.scalars(select(EventType).order_by(EventType.name)))


@router.post("", response_model=EventTypeRead, status_code=201)
def create_event_type(payload: EventTypeCreate, db: Session = Depends(get_db)) -> EventType:
    """Create a reusable event type, or return the existing one if duplicated."""

    normalized_name = normalize_event_name(payload.name)
    # Case-insensitive lookup prevents "sangeet" and "Sangeet" from becoming
    # separate event type records.
    existing_event_type = db.scalar(
        select(EventType).where(func.lower(EventType.name) == normalized_name.lower())
    )
    if existing_event_type is not None:
        return existing_event_type

    event_type = EventType(name=normalized_name, status=payload.status)
    db.add(event_type)
    db.commit()
    db.refresh(event_type)
    return event_type
