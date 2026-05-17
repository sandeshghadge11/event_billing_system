from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _quote_mysql_identifier(identifier: str) -> str:
    """Escape a MySQL database/table identifier for use in CREATE DATABASE."""

    return f"`{identifier.replace('`', '``')}`"


def _database_bootstrap_url(database_url: URL) -> URL:
    """Return a MySQL URL that connects to an always-present system database."""

    return database_url.set(database="mysql")


def ensure_database_exists() -> None:
    """Create the configured MySQL database before SQLAlchemy creates tables."""

    database_url = make_url(settings.database_url)
    database_name = database_url.database

    # SQLite creates its database file automatically, and other engines can be
    # handled later if needed. MySQL needs the database/schema to exist first.
    if not database_url.drivername.startswith("mysql") or not database_name:
        return

    bootstrap_engine = create_engine(_database_bootstrap_url(database_url), pool_pre_ping=True)
    with bootstrap_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE DATABASE IF NOT EXISTS "
                f"{_quote_mysql_identifier(database_name)} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
    bootstrap_engine.dispose()


ensure_database_exists()

# Engine owns the actual database connection pool. pool_pre_ping checks stale
# MySQL connections before using them, which helps after the DB has been idle.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# SessionLocal is a factory. API dependencies call it to get a short-lived
# database session for exactly one request.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class that all SQLAlchemy models inherit from."""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that opens a DB session and always closes it."""

    db = SessionLocal()
    try:
        # The route handler receives this session through Depends(get_db).
        yield db
    finally:
        # Closing here prevents connection leaks even if a route raises an error.
        db.close()
