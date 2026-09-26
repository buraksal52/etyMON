"""Create the documented Phase 1 development dataset."""

from app.db.seed import seed_development_data
from app.db.session import SessionLocal


def main() -> None:
    with SessionLocal() as db:
        counts = seed_development_data(db)
    print(f"Seeded development data: {counts}")


if __name__ == "__main__":
    main()
