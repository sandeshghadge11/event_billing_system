from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EventType(Base):
    __tablename__ = "event_types"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="Active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
