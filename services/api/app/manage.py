"""Local-only schema/provisioning commands, no remote DB defaults."""

import argparse
import getpass
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command

from .demo_data import seed_demo_studies
from .models import AuditEvent, Clinic, Membership, User
from .runtime import load_local_env
from .security import hash_password


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "bootstrap-admin", "seed-demo", "seed-studies"])
    args = parser.parse_args()
    env_path = load_local_env()
    if args.command == "migrate":
        cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        cfg.attributes["database_url"] = os.environ["DEV_ADMIN_DATABASE_URL"]
        command.upgrade(cfg, "head")
        print("Migrated local development database.")
        return
    if args.command == "seed-studies":
        url = make_url(os.environ["DEV_DATABASE_URL"])
        if url.host not in {"127.0.0.1", "localhost"} or url.database != "familydent_dev":
            raise SystemExit("Synthetic seeding is restricted to the local familydent_dev database")
        engine = create_engine(url, hide_parameters=True)
        try:
            with Session(engine) as db, db.begin():
                counts = seed_demo_studies(db, datetime.now(UTC))
            print("Synthetic metadata added: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
        finally:
            engine.dispose()
        return
    engine = create_engine(os.environ["DEV_DATABASE_URL"], hide_parameters=True)
    with Session(engine) as db, db.begin():
        if db.scalar(select(func.count()).select_from(User)):
            raise SystemExit(
                "Refusing bootstrap: accounts already exist. Use authenticated account management."
            )
        if args.command == "bootstrap-admin":
            email = input("Verified administrator email: ").strip().lower()
            if email.count("@") != 1:
                raise SystemExit("Invalid email")
            password = getpass.getpass("Initial password (12–128 characters): ")
            if password != getpass.getpass("Repeat password: "):
                raise SystemExit("Passwords do not match")
            db.add(
                User(
                    email=email,
                    display_name="FamilyDent administrator",
                    role="platform_admin",
                    password_hash=hash_password(password),
                )
            )
        else:
            # Synthetic-only demo; credentials never enter command arguments or stdout.
            credentials = {}
            clinic = Clinic(name="SYNTHETIC CLINIC")
            db.add(clinic)
            db.flush()
            for name, role in [
                ("admin", "platform_admin"),
                ("staff", "imaging_staff"),
                ("doctor", "doctor"),
                ("other", "doctor"),
            ]:
                password = secrets.token_urlsafe(20)
                user = User(
                    email=name + "@example.test",
                    display_name="SYNTHETIC " + name,
                    role=role,
                    password_hash=hash_password(password),
                )
                db.add(user)
                db.flush()
                if role == "doctor":
                    db.add(Membership(user_id=user.id, clinic_id=clinic.id))
                credentials[name + "@example.test"] = password
            target = env_path.with_name(".demo-credentials")
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(
                    "SYNTHETIC LOCAL ACCOUNTS ONLY\n"
                    + "".join(f"{email} {pwd}\n" for email, pwd in credentials.items())
                )
        db.add(
            AuditEvent(
                action="bootstrap.accounts",
                result="success",
                request_id=str(uuid4()),
                created_at=datetime.now(UTC),
            )
        )
    engine.dispose()
    print("Accounts provisioned. TOTP enrollment is required at first login.")


if __name__ == "__main__":
    main()
