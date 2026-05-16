from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClientBase(BaseModel):
    name: str
    mobile: str
    address: str | None = None
    notes: str | None = None


class ClientCreate(ClientBase):
    pass


class ClientRead(ClientBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
