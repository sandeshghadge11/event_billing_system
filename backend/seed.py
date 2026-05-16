from app.core.database import Base, SessionLocal, engine
from app.services.seed import seed_database


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    print("Seed data loaded.")


if __name__ == "__main__":
    main()
