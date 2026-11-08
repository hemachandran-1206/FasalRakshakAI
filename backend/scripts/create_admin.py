"""Create (or reset the password of) an admin account.   python scripts/create_admin.py
Admins cannot sign up through the website; this is the only way to make one."""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import User  # noqa: E402
from app.services import security  # noqa: E402


def main():
    Base.metadata.create_all(engine)
    email = input("Admin email: ").strip().lower()
    name = input("Full name: ").strip() or "Admin"
    password = getpass.getpass(f"Password (min {security.MIN_PASSWORD_LENGTH} chars): ")
    if "@" not in email or len(password) < security.MIN_PASSWORD_LENGTH:
        sys.exit("Invalid email or password too short.")
    if password != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match.")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            if user.role != "admin":
                sys.exit("That email belongs to a non-admin account.")
            user.password_hash, user.full_name = security.hash_password(password), name
            print("Existing admin: password updated.")
        else:
            db.add(User(email=email, full_name=name, role="admin", password_hash=security.hash_password(password)))
            print("Admin created.")
        db.commit()


if __name__ == "__main__":
    main()
