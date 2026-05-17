from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientRead

router = APIRouter()


@router.get("", response_model=list[ClientRead])
def list_clients(db: Session = Depends(get_db)) -> list[Client]:
    """Return all clients sorted by name for dropdowns/search screens."""

    # FastAPI injects db from get_db(); SQLAlchemy executes the SELECT query.
    return list(db.scalars(select(Client).order_by(Client.name)))


@router.post("", response_model=ClientRead, status_code=201)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)) -> Client:
    """Create a client record before a booking is created for that client."""

    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Client name is required")
    if not payload.mobile.strip():
        raise HTTPException(status_code=400, detail="Mobile number is required")

    # payload is a Pydantic schema; model_dump() converts it to normal kwargs
    # that match the SQLAlchemy Client model fields.
    client = Client(**payload.model_dump())
    db.add(client)
    # commit writes the new row; refresh loads generated fields such as id.
    db.commit()
    db.refresh(client)
    return client
