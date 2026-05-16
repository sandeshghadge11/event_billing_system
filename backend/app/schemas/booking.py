from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.schemas.client import ClientRead


class EventLineItemBase(BaseModel):
    item_id: int | None = None
    material_name: str
    quantity: Decimal = Decimal("1")
    rate: Decimal = Decimal("0")
    notes: str | None = None


class EventLineItemCreate(EventLineItemBase):
    pass


class EventLineItemRead(EventLineItemBase):
    id: int

    @computed_field
    @property
    def amount(self) -> Decimal:
        return self.quantity * self.rate

    model_config = ConfigDict(from_attributes=True)


class BookingEventBase(BaseModel):
    name: str
    event_date: date | None = None
    venue: str | None = None
    event_time: str | None = None
    notes: str | None = None


class BookingEventCreate(BookingEventBase):
    line_items: list[EventLineItemCreate] = Field(default_factory=list)


class BookingEventRead(BookingEventBase):
    id: int
    line_items: list[EventLineItemRead] = Field(default_factory=list)

    @computed_field
    @property
    def subtotal(self) -> Decimal:
        return sum((line.amount for line in self.line_items), Decimal("0"))

    model_config = ConfigDict(from_attributes=True)


class PaymentBase(BaseModel):
    amount: Decimal
    payment_date: date | None = None
    mode: str = "Cash"
    notes: str | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentRead(PaymentBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class BookingCreate(BaseModel):
    booking_no: str
    title: str
    client_id: int
    start_date: date | None = None
    end_date: date | None = None
    status: str = "Draft"
    notes: str | None = None
    events: list[BookingEventCreate] = Field(default_factory=list)


class BookingRead(BaseModel):
    id: int
    booking_no: str
    title: str
    client_id: int
    start_date: date | None = None
    end_date: date | None = None
    status: str
    notes: str | None = None
    created_at: datetime
    client: ClientRead
    events: list[BookingEventRead] = Field(default_factory=list)
    payments: list[PaymentRead] = Field(default_factory=list)

    @computed_field
    @property
    def subtotal(self) -> Decimal:
        return sum((event.subtotal for event in self.events), Decimal("0"))

    @computed_field
    @property
    def paid(self) -> Decimal:
        return sum((payment.amount for payment in self.payments), Decimal("0"))

    @computed_field
    @property
    def balance(self) -> Decimal:
        return self.subtotal - self.paid

    model_config = ConfigDict(from_attributes=True)
