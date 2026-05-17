from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ItemBase(BaseModel):
    """Shared material master fields for create and read APIs."""

    name: str
    category: str = "FX Light"
    unit: str = "Piece"
    default_rate: Decimal = Decimal("0")
    status: str = "Active"


class ItemCreate(ItemBase):
    """Request body for adding a material master item."""

    pass


class ItemRead(ItemBase):
    """Response body for material master items."""

    id: int
    created_at: datetime

    # Allows the API to return SQLAlchemy Item objects as JSON.
    model_config = ConfigDict(from_attributes=True)
