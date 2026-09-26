"""Report database counts without creating demo data."""

from app.db.seed import seed_development_data
from app.db.session import SessionLocal


def main() -> None:
    with SessionLocal() as db:
        counts = seed_development_data(db)
    print(f"No demo data created. Current database counts: {counts}")


if __name__ == "__main__":
    main()
