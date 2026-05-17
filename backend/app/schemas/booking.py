from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.schemas.client import ClientRead


class EventLineItemBase(BaseModel):
    """Fields shared by create/read schemas for event material rows."""

    item_id: int | None = None
    material_name: str
    quantity: Decimal = Decimal("1")
    rate: Decimal = Decimal("0")
    notes: str | None = None


class EventLineItemCreate(EventLineItemBase):
    """Request body shape when the frontend adds a material to an event."""

    pass


class EventLineItemRead(EventLineItemBase):
    """Response shape for a material row returned by the API."""

    id: int

    @computed_field
    @property
    def amount(self) -> Decimal:
        """Line total calculated from quantity and rate for API responses."""

        return self.quantity * self.rate

    # from_attributes lets Pydantic read values directly from SQLAlchemy objects.
    model_config = ConfigDict(from_attributes=True)


class BookingEventBase(BaseModel):
    """Fields shared by booking-event create and read operations."""

    name: str
    event_date: date | None = None
    venue: str | None = None
    event_time: str | None = None
    status: str = "Pending"
    is_active: bool = True
    notes: str | None = None


class BookingEventCreate(BookingEventBase):
    """Request body for adding an event, including optional nested line items."""

    line_items: list[EventLineItemCreate] = Field(default_factory=list)


class BookingEventRead(BookingEventBase):
    """Response body for an event with its billed material rows."""

    id: int
    line_items: list[EventLineItemRead] = Field(default_factory=list)

    @computed_field
    @property
    def subtotal(self) -> Decimal:
        """Event total shown in the booking and invoice response."""

        return sum((line.amount for line in self.line_items), Decimal("0"))

    model_config = ConfigDict(from_attributes=True)


class PaymentBase(BaseModel):
    """Fields shared by payment create/read schemas."""

    amount: Decimal
    payment_date: date | None = None
    mode: str = "Cash"
    notes: str | None = None


class PaymentCreate(PaymentBase):
    """Request body for recording a booking payment."""

    pass


class PaymentRead(PaymentBase):
    """Response body for payment rows linked to a booking."""

    id: int

    model_config = ConfigDict(from_attributes=True)


class BookingMailRequest(BaseModel):
    """Request body for sending a booking bill over email."""

    receiver_email: str | None = None
    sender_email: str | None = None


class BookingCreate(BaseModel):
    """Request body used by POST /api/bookings."""

    booking_no: str
    title: str
    client_id: int
    start_date: date | None = None
    end_date: date | None = None
    status: str = "Pending"
    notes: str | None = None
    events: list[BookingEventCreate] = Field(default_factory=list)


class BookingRead(BaseModel):
    """Full booking response returned to the React frontend."""

    id: int
    booking_no: str
    title: str
    client_id: int
    start_date: date | None = None
    end_date: date | None = None
    status: str
    is_active: bool = True
    notes: str | None = None
    created_at: datetime
    client: ClientRead
    events: list[BookingEventRead] = Field(default_factory=list)
    payments: list[PaymentRead] = Field(default_factory=list)

    @computed_field
    @property
    def subtotal(self) -> Decimal:
        """Total billing amount across all events."""

        return sum((event.subtotal for event in self.events), Decimal("0"))

    @computed_field
    @property
    def paid(self) -> Decimal:
        """Total payments received for this booking."""

        return sum((payment.amount for payment in self.payments), Decimal("0"))

    @computed_field
    @property
    def balance(self) -> Decimal:
        """Pending balance calculated for the frontend and invoice."""

        return self.subtotal - self.paid

    model_config = ConfigDict(from_attributes=True)
