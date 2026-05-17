from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Client(Base):
    """Customer/contact details used by bookings and invoices."""

    __tablename__ = "clients"

    # Mobile is the unique natural key used to reuse existing clients.
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    mobile: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    address: Mapped[str | None] = mapped_column(String(255), default=None)
    notes: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # A client can have many bookings. Deleting a client removes their bookings
    # through SQLAlchemy's cascade behavior.
    bookings = relationship("Booking", back_populates="client", cascade="all, delete-orphan")
