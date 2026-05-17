from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemRead

router = APIRouter()


@router.get("", response_model=list[ItemRead])
def list_items(db: Session = Depends(get_db)) -> list[Item]:
    """Return material master items used by the frontend line-item modal."""

    return list(db.scalars(select(Item).order_by(Item.name)))


@router.post("", response_model=ItemRead, status_code=201)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> Item:
    """Create one material master item with its default rate and unit."""

    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Material name is required")
    if not payload.category.strip():
        raise HTTPException(status_code=400, detail="Category is required")
    if not payload.unit.strip():
        raise HTTPException(status_code=400, detail="Unit is required")

    item = Item(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
