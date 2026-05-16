from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    booking_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    start_date: Mapped[date | None] = mapped_column(Date, default=None)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    status: Mapped[str] = mapped_column(String(30), default="Draft")
    notes: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="bookings")
    events = relationship("BookingEvent", back_populates="booking", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="booking", cascade="all, delete-orphan")


class BookingEvent(Base):
    __tablename__ = "booking_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"))
    name: Mapped[str] = mapped_column(String(80))
    event_date: Mapped[date | None] = mapped_column(Date, default=None)
    venue: Mapped[str | None] = mapped_column(String(160), default=None)
    event_time: Mapped[str | None] = mapped_column(String(80), default=None)
    notes: Mapped[str | None] = mapped_column(String(500), default=None)

    booking = relationship("Booking", back_populates="events")
    line_items = relationship("EventLineItem", back_populates="event", cascade="all, delete-orphan")


class EventLineItem(Base):
    __tablename__ = "event_line_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("booking_events.id"))
    item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id"), default=None)
    material_name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=1)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(String(500), default=None)

    event = relationship("BookingEvent", back_populates="line_items")
    item = relationship("Item")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_date: Mapped[date | None] = mapped_column(Date, default=None)
    mode: Mapped[str] = mapped_column(String(40), default="Cash")
    notes: Mapped[str | None] = mapped_column(String(500), default=None)

    booking = relationship("Booking", back_populates="payments")
