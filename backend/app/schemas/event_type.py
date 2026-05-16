from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventTypeBase(BaseModel):
    name: str
    status: str = "Active"


class EventTypeCreate(EventTypeBase):
    pass


class EventTypeRead(EventTypeBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
