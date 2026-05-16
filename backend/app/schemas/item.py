from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ItemBase(BaseModel):
    name: str
    category: str = "FX Light"
    unit: str = "Piece"
    default_rate: Decimal = Decimal("0")
    status: str = "Active"


class ItemCreate(ItemBase):
    pass


class ItemRead(ItemBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
