from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Client(Base):
    """Customer/contact details used by bookings and invoices."""

    __tablename__ = "clients"

    # name and mobile are indexed because they are natural search fields.
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    mobile: Mapped[str] = mapped_column(String(20), index=True)
    address: Mapped[str | None] = mapped_column(String(255), default=None)
    notes: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # A client can have many bookings. Deleting a client removes their bookings
    # through SQLAlchemy's cascade behavior.
    bookings = relationship("Booking", back_populates="client", cascade="all, delete-orphan")
