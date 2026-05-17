from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CompanySettingsBase(BaseModel):
    """Editable company settings shared by invoices and email delivery."""

    company_name: str
    invoice_prefix: str
    owner_mobile: str
    default_advance: Decimal = Decimal("0")
    send_mail: str
    recv_mail: str


class CompanySettingsUpdate(CompanySettingsBase):
    """Request body for saving company settings."""

    pass


class CompanySettingsRead(CompanySettingsBase):
    """Response body for the saved company settings row."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
