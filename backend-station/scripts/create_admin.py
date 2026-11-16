"""Create the first administrator without storing plaintext credentials."""

import argparse

from app.core.security import hash_password
from app.database import SessionLocal
from app.tables import User
from sqlalchemy import select

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    parser.add_argument("--dni", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    with SessionLocal.begin() as db:
        if db.scalar(select(User).where(User.role == "ADMIN")) is not None:
            raise SystemExit("An administrator already exists")
        db.add(
            User(
                first_name=args.first_name,
                last_name=args.last_name,
                dni=args.dni,
                email=args.email.lower(),
                password_hash=hash_password(args.password),
                role="ADMIN",
            )
        )
    print("Administrator created")
