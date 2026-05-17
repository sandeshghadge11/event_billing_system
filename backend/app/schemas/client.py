from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClientBase(BaseModel):
    """Shared client fields used when creating and reading customers."""

    name: str
    mobile: str
    address: str | None = None
    notes: str | None = None


class ClientCreate(ClientBase):
    """Request body for creating a new client."""

    pass


class ClientRead(ClientBase):
    """Response body for client records returned from the database."""

    id: int
    created_at: datetime

    # Allows Pydantic to serialize SQLAlchemy Client model instances.
    model_config = ConfigDict(from_attributes=True)
