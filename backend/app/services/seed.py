from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingEvent, EventLineItem, Payment
from app.models.client import Client
from app.models.item import Item


STARTER_ITEMS = [
    ("Laser", "FX Light", "Piece", Decimal("6500")),
    ("LED Par", "LED Light", "Piece", Decimal("750")),
    ("LED Wall", "Display", "Package", Decimal("30000")),
    ("Sharpee", "Moving Light", "Piece", Decimal("2500")),
    ("Other FX Lights", "FX Package", "Package", Decimal("8500")),
]


def seed_database(db: Session) -> None:
    for name, category, unit, rate in STARTER_ITEMS:
        existing_item = db.scalar(select(Item).where(Item.name == name))
        if existing_item is None:
            db.add(Item(name=name, category=category, unit=unit, default_rate=rate))

    existing_booking = db.scalar(select(Booking).where(Booking.booking_no == "1003"))
    if existing_booking is None:
        client = Client(
            name="Bandu Waghmare",
            mobile="7845368678",
            address="Geeta Nagar",
        )
        booking = Booking(
            booking_no="1003",
            title="Waghmare Wedding",
            start_date=date(2024, 12, 26),
            end_date=date(2024, 12, 29),
            status="Confirmed",
            client=client,
        )

        booking.events.extend(
            [
                BookingEvent(
                    name="Sangeet",
                    event_date=date(2024, 12, 26),
                    venue="Geeta Hall",
                    line_items=[
                        EventLineItem(material_name="Laser", quantity=Decimal("2"), rate=Decimal("6500")),
                        EventLineItem(material_name="LED Par", quantity=Decimal("12"), rate=Decimal("750")),
                        EventLineItem(material_name="Sharpee", quantity=Decimal("4"), rate=Decimal("2500")),
                    ],
                ),
                BookingEvent(
                    name="Haldi",
                    event_date=date(2024, 12, 27),
                    venue="Home Lawn",
                    line_items=[
                        EventLineItem(material_name="LED Par", quantity=Decimal("8"), rate=Decimal("750")),
                        EventLineItem(material_name="Other FX Lights", quantity=Decimal("1"), rate=Decimal("8500")),
                    ],
                ),
                BookingEvent(
                    name="Saptpadi",
                    event_date=date(2024, 12, 28),
                    venue="Geeta Hall",
                    line_items=[
                        EventLineItem(material_name="Laser", quantity=Decimal("1"), rate=Decimal("6500")),
                        EventLineItem(material_name="Sharpee", quantity=Decimal("6"), rate=Decimal("2500")),
                    ],
                ),
                BookingEvent(
                    name="Reception",
                    event_date=date(2024, 12, 29),
                    venue="Geeta Hall",
                    line_items=[
                        EventLineItem(material_name="LED Wall", quantity=Decimal("1"), rate=Decimal("30000")),
                        EventLineItem(material_name="Sharpee", quantity=Decimal("8"), rate=Decimal("2500")),
                        EventLineItem(material_name="Laser", quantity=Decimal("2"), rate=Decimal("6500")),
                    ],
                ),
            ]
        )
        booking.payments.append(
            Payment(amount=Decimal("50000"), payment_date=date(2024, 12, 20), mode="UPI")
        )
        db.add(booking)

    db.commit()
