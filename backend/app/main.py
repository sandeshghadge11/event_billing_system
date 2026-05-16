from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import bookings, clients, items
from app.core.config import settings
from app.core.database import Base, engine

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["bookings"])
app.include_router(items.router, prefix="/api/items", tags=["items"])


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.on_event("startup")
def create_database_tables() -> None:
    Base.metadata.create_all(bind=engine)
