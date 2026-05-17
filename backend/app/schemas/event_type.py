from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventTypeBase(BaseModel):
    """Shared fields for reusable event type names."""

    name: str
    status: str = "Active"


class EventTypeCreate(EventTypeBase):
    """Request body for creating an event type."""

    pass


class EventTypeRead(EventTypeBase):
    """Response body for event type records."""

    id: int
    created_at: datetime

    # Allows Pydantic to read SQLAlchemy EventType objects.
    model_config = ConfigDict(from_attributes=True)
