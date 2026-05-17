from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CompanySettings(Base):
    """Single row of company and invoice settings used across the app."""

    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    company_name: Mapped[str] = mapped_column(String(160), default="Prasad FX Lights")
    invoice_prefix: Mapped[str] = mapped_column(String(20), default="PFX")
    owner_mobile: Mapped[str] = mapped_column(String(30), default="+91 98765 43210")
    default_advance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    send_mail: Mapped[str] = mapped_column(String(160), default="sandeshghadge301@gmail.com")
    recv_mail: Mapped[str] = mapped_column(String(160), default="sandeshghadge301@gmail.com")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
