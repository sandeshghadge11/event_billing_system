from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Booking(Base):
    """Main booking/order header for one wedding or event package."""

    __tablename__ = "bookings"

    # Parent booking fields shown in the booking list and invoice header.
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    booking_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    start_date: Mapped[date | None] = mapped_column(Date, default=None)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    status: Mapped[str] = mapped_column(String(30), default="Pending")
    # Some existing local databases already have this required column. Keeping
    # it in the model makes INSERT statements include a value instead of failing.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships connect this parent booking to the client, event rows, and
    # payment rows. The API can access booking.events or booking.payments from
    # these attributes.
    client = relationship("Client", back_populates="bookings")
    # delete-orphan means child event/payment rows are removed when the booking
    # is deleted or when they are detached from this booking.
    events = relationship("BookingEvent", back_populates="booking", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="booking", cascade="all, delete-orphan")


class BookingEvent(Base):
    """One ceremony/function inside a booking, for example Sangeet or Haldi."""

    __tablename__ = "booking_events"

    # booking_id links the event back to bookings.id.
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"))
    name: Mapped[str] = mapped_column(String(80))
    event_date: Mapped[date | None] = mapped_column(Date, default=None)
    venue: Mapped[str | None] = mapped_column(String(160), default=None)
    event_time: Mapped[str | None] = mapped_column(String(80), default=None)
    # Existing local databases may require an event status column. The frontend
    # does not edit it yet, so new events default to Pending.
    status: Mapped[str] = mapped_column(String(30), default="Pending")
    # Older local booking_events tables may also require is_active. Including it
    # keeps event inserts compatible with those existing databases.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(String(500), default=None)

    booking = relationship("Booking", back_populates="events")
    # Each event owns the material line items billed for that event.
    line_items = relationship("EventLineItem", back_populates="event", cascade="all, delete-orphan")


class EventLineItem(Base):
    """Material, quantity, and rate charged under a specific booking event."""

    __tablename__ = "event_line_items"

    # item_id is optional because users may type a material name that is not yet
    # in the material master table.
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("booking_events.id"))
    item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id"), default=None)
    material_name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=1)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(String(500), default=None)

    event = relationship("BookingEvent", back_populates="line_items")
    # Optional lookup relationship to the material master.
    item = relationship("Item")


class Payment(Base):
    """Money received for a booking, used to calculate pending balance."""

    __tablename__ = "payments"

    # booking_id links every payment to the booking whose balance it reduces.
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_date: Mapped[date | None] = mapped_column(Date, default=None)
    mode: Mapped[str] = mapped_column(String(40), default="Cash")
    notes: Mapped[str | None] = mapped_column(String(500), default=None)

    booking = relationship("Booking", back_populates="payments")
