from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import bookings, clients, company_settings, event_types, items
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.services.seed import seed_database

# FastAPI application object. All API routers below are attached to this object,
# so Uvicorn runs this module as the backend entry point.
app = FastAPI(title=settings.app_name)

# Allow the React frontend to call this API from the Vite development origin.
# The frontend uses fetch(), so CORS must be enabled before the route handlers
# are reached.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+):5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Each router owns one part of the API. The prefix here becomes the first part
# of the URL, and the route decorators inside each file add the rest.
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["bookings"])
app.include_router(items.router, prefix="/api/items", tags=["items"])
app.include_router(event_types.router, prefix="/api/event-types", tags=["event-types"])
app.include_router(company_settings.router, prefix="/api/company-settings", tags=["company-settings"])


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Small endpoint used to verify that the backend process is reachable."""
    return {"status": "ok", "app": settings.app_name}


@app.on_event("startup")
def create_database_tables() -> None:
    """Create missing database tables and starter dropdown values on startup."""

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
