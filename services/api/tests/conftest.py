import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from app.config import Settings
from app.main import create_app
from app.models import Base, Clinic, Membership, User
from app.security import hash_password

ROOT = Path(__file__).resolve().parents[3]
for line in (ROOT / "infra/local/.env").read_text().splitlines():
    if line and not line.startswith("#"):
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


@pytest.fixture(scope="session")
def engines():
    admin_url = os.environ["TEST_ADMIN_DATABASE_URL"]
    assert admin_url.endswith("/familydent_test"), "Only dedicated synthetic test database is permitted"
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = admin_url
    command.upgrade(cfg, "head")
    admin = create_engine(admin_url)
    app = create_engine(os.environ["TEST_DATABASE_URL"])
    yield admin, app
    admin.dispose()
    app.dispose()


@pytest.fixture
def env(engines):
    admin, engine = engines
    with admin.begin() as connection:
        names = ",".join('"' + t.name + '"' for t in Base.metadata.sorted_tables)
        connection.execute(text("TRUNCATE " + names + " CASCADE"))
    clock = [datetime(2031, 1, 1, 12, 0, tzinfo=UTC)]
    settings = Settings(
        database_url=os.environ["TEST_DATABASE_URL"],
        totp_key=os.environ["TOTP_KEY"],
        auth_key=os.environ["AUTH_KEY"],
        public_origin="http://testserver",
        development=True,
    )
    app = create_app(settings, now=lambda: clock[0])
    password = "Synthetic-test-password-42!"
    ids = {}
    with Session(engine) as db, db.begin():
        clinic = Clinic(name="SYNTHETIC CLINIC")
        db.add(clinic)
        db.flush()
        ids["clinic"] = str(clinic.id)
        for name, role in [
            ("staff", "imaging_staff"),
            ("doctor", "doctor"),
            ("other", "doctor"),
            ("admin", "platform_admin"),
        ]:
            user = User(
                email=name + "@example.test",
                display_name="SYNTHETIC " + name,
                role=role,
                password_hash=hash_password(password),
            )
            db.add(user)
            db.flush()
            ids[name] = str(user.id)
            if role == "doctor":
                db.add(Membership(user_id=user.id, clinic_id=clinic.id))
    with TestClient(app) as client:
        client.headers["Origin"] = "http://testserver"
        yield {
            "client": client,
            "app": app,
            "engine": engine,
            "admin_engine": admin,
            "clock": clock,
            "ids": ids,
            "password": password,
        }
    app.state.engine.dispose()


def login(env, name="doctor"):
    client = env["client"]
    assert (
        client.post(
            "/api/auth/password", json={"email": name + "@example.test", "password": env["password"]}
        ).status_code
        == 200
    )
    secret_response = client.post("/api/auth/totp/enroll")
    if secret_response.status_code == 200:
        secret = secret_response.json()["secret"]
    else:
        from app.security import decrypt_secret

        with Session(env["engine"]) as db:
            secret = decrypt_secret(
                db.get(User, uuid.UUID(env["ids"][name])).totp_secret, env["app"].state.settings
            )
    import pyotp

    code = pyotp.TOTP(secret).at(env["clock"][0])
    response = client.post("/api/auth/totp", json={"code": code})
    assert response.status_code == 200, response.text
    me = client.get("/api/auth/me").json()
    client.headers["X-CSRF-Token"] = me["csrf_token"]
    return secret
