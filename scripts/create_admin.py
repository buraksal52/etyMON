#!/usr/bin/env python3
"""Create or update a real organizer account for local/admin bootstrap."""

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.auth import hash_password, normalize_email  # noqa: E402
from app.db.models import Organizer  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    password = getpass.getpass("Admin password: ")
    if not password:
        raise SystemExit("Password cannot be empty")

    email = normalize_email(args.email)
    with SessionLocal() as db:
        organizer = db.query(Organizer).filter_by(email=email).one_or_none()
        if organizer is None:
            organizer = Organizer(email=email, name=args.name, password_hash_or_auth_provider_id="")
            db.add(organizer)
        organizer.name = args.name
        organizer.password_hash_or_auth_provider_id = hash_password(password)
        db.commit()
    print(f"Admin ready: {email}")


if __name__ == "__main__":
    main()
