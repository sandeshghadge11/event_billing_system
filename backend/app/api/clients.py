from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientRead

router = APIRouter()


@router.get("", response_model=list[ClientRead])
def list_clients(db: Session = Depends(get_db)) -> list[Client]:
    return list(db.scalars(select(Client).order_by(Client.name)))


@router.post("", response_model=ClientRead, status_code=201)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)) -> Client:
    client = Client(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client
