from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.company_settings import CompanySettings
from app.schemas.company_settings import CompanySettingsRead, CompanySettingsUpdate

router = APIRouter()


def get_or_create_settings(db: Session) -> CompanySettings:
    settings = db.get(CompanySettings, 1)
    if settings is not None:
        return settings

    settings = CompanySettings(id=1)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


@router.get("", response_model=CompanySettingsRead)
def read_company_settings(db: Session = Depends(get_db)) -> CompanySettings:
    """Return the saved company settings used for invoices and bill email."""

    return get_or_create_settings(db)


@router.put("", response_model=CompanySettingsRead)
def save_company_settings(
    payload: CompanySettingsUpdate,
    db: Session = Depends(get_db),
) -> CompanySettings:
    """Save editable company settings in the database."""

    if not payload.company_name.strip():
        raise HTTPException(status_code=400, detail="Company name is required")
    if not payload.invoice_prefix.strip():
        raise HTTPException(status_code=400, detail="Invoice prefix is required")
    if "@" not in payload.send_mail:
        raise HTTPException(status_code=400, detail="Send mail must be a valid email")
    if "@" not in payload.recv_mail:
        raise HTTPException(status_code=400, detail="Receiver mail must be a valid email")
    if payload.default_advance < Decimal("0"):
        raise HTTPException(status_code=400, detail="Default advance cannot be negative")

    settings = get_or_create_settings(db)
    settings.company_name = payload.company_name.strip()
    settings.invoice_prefix = payload.invoice_prefix.strip()
    settings.owner_mobile = payload.owner_mobile.strip()
    settings.default_advance = payload.default_advance
    settings.send_mail = payload.send_mail.strip()
    settings.recv_mail = payload.recv_mail.strip()
    db.commit()
    db.refresh(settings)
    return settings
