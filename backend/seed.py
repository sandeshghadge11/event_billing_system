from app.core.database import Base, SessionLocal, engine
from app.services.seed import seed_database


def main() -> None:
    """Create tables and load starter rows from the command line."""

    # Keep the manual seed command aligned with FastAPI startup table creation.
    Base.metadata.create_all(bind=engine)
    # SessionLocal opens a DB session; the context manager closes it afterward.
    with SessionLocal() as db:
        seed_database(db)
    print("Seed data loaded.")


if __name__ == "__main__":
    # Allows `python seed.py` to execute the setup script directly.
    main()
