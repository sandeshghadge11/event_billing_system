from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event_type import EventType
from app.models.item import Item


# Starter material master rows used when setting up a fresh local database.
STARTER_ITEMS = [
    ("Laser", "FX Light", "Piece", Decimal("6500")),
    ("LED Par", "LED Light", "Piece", Decimal("750")),
    ("LED Wall", "Display", "Package", Decimal("30000")),
    ("Sharpee", "Moving Light", "Piece", Decimal("2500")),
    ("Other FX Lights", "FX Package", "Package", Decimal("8500")),
]

# Starter event names used by the booking workflow.
STARTER_EVENT_TYPES = [
    "Sangeet",
    "Haldi",
    "Saptpadi",
    "Reception",
]


def seed_database(db: Session) -> None:
    """Insert starter items/event types without duplicating existing rows."""

    for name, category, unit, rate in STARTER_ITEMS:
        # Check by item name first so running the seed command repeatedly is safe.
        existing_item = db.scalar(select(Item).where(Item.name == name))
        if existing_item is None:
            db.add(Item(name=name, category=category, unit=unit, default_rate=rate))

    for name in STARTER_EVENT_TYPES:
        # Event type names are also unique; skip anything already present.
        existing_event_type = db.scalar(select(EventType).where(EventType.name == name))
        if existing_event_type is None:
            db.add(EventType(name=name))

    # One commit writes all missing starter rows together.
    db.commit()
