from dataclasses import replace
from datetime import timedelta
from uuid import UUID

from conftest import login
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_assignments import create_study

from app.main import create_app
from app.models import AuditEvent, AuthChallenge, User


def test_cookie_flags_and_validation_do_not_echo_credentials(env):
    settings = replace(env["app"].state.settings, development=False, public_origin="https://testserver")
    with TestClient(create_app(settings), base_url="https://testserver") as client:
        response = client.post(
            "/api/auth/password",
            json={"email": "doctor@example.test", "password": env["password"]},
            headers={"Origin": "https://testserver"},
        )
        assert response.status_code == 200
        assert all(
            value in response.headers["set-cookie"] for value in ("Secure", "HttpOnly", "SameSite=strict")
        )
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/api/auth/me").status_code == 401
        malformed = client.post(
            "/api/auth/password",
            json={"email": "doctor@example.test", "password": env["password"], "role": "platform_admin"},
            headers={"Origin": "https://testserver"},
        )
        assert malformed.status_code == 422
        assert env["password"] not in malformed.text


def test_membership_revoke_blocks_existing_doctor_session(env):
    from fastapi.testclient import TestClient

    login(env, "staff")
    c = env["client"]
    study = create_study(env)
    assert (
        c.post(
            f"/api/staff/studies/{study}/assignments",
            json={"doctor_id": env["ids"]["doctor"], "clinic_id": env["ids"]["clinic"]},
        ).status_code
        == 201
    )
    login(env, "doctor")
    assert c.get(f"/api/doctor/studies/{study}").status_code == 200
    with TestClient(env["app"]) as admin:
        admin.headers["Origin"] = "http://testserver"
        login({**env, "client": admin}, "admin")
        assert (
            admin.post(
                f"/api/admin/memberships/{env['ids']['doctor']}/{env['ids']['clinic']}/revoke"
            ).status_code
            == 204
        )
    assert c.get("/api/doctor/studies").json()["total"] == 0
    assert c.get(f"/api/doctor/studies/{study}").status_code == 404


def test_staff_cannot_escalate_and_audit_never_contains_credentials(env):
    c = env["client"]
    login(env, "staff")
    body = {
        "email": "new@example.test",
        "display_name": "SYNTHETIC NEW",
        "role": "imaging_staff",
        "password": "Synthetic-new-user-password42",
    }
    assert c.post("/api/admin/users", json=body).status_code == 403
    body["role"] = "doctor"
    body["clinic_id"] = env["ids"]["clinic"]
    response = c.post("/api/admin/users", json=body)
    assert response.status_code == 201
    assert body["password"] not in response.text
    assert c.get("/api/staff/doctors").status_code == 200
    assert c.get("/api/admin/users").status_code == 403
    with Session(env["engine"]) as db:
        for event in db.scalars(select(AuditEvent)):
            assert not any(secret in repr(event.__dict__) for secret in (env["password"], body["password"]))
        user = db.get(User, UUID(response.json()["id"]))
        assert user.totp_secret is None
        assert user.password_hash.startswith("$argon2id$")


def test_ip_limit_and_literal_search_do_not_expand_scope(env):
    c = env["client"]
    for n in range(30):
        assert (
            c.post(
                "/api/auth/password", json={"email": f"unknown{n}@example.test", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        c.post("/api/auth/password", json={"email": "another@example.test", "password": "wrong"}).status_code
        == 429
    )
    env["clock"][0] += timedelta(minutes=16)
    login(env, "staff")
    study = create_study(env)
    c.post(
        f"/api/staff/studies/{study}/assignments",
        json={"doctor_id": env["ids"]["doctor"], "clinic_id": env["ids"]["clinic"]},
    )
    login(env)
    assert c.get("/api/doctor/studies?q=%25").json()["total"] == 0
    assert c.get("/api/doctor/studies?limit=0").status_code == 422
    with Session(env["engine"]) as db:
        assert db.scalar(select(AuthChallenge).where(AuthChallenge.consumed_at.is_(None))) is None


def test_patient_lookup_is_audited(env):
    c = env["client"]
    login(env, "staff")
    created = c.post(
        "/api/staff/patients", json={"local_identifier": "SYN-LOOKUP", "display_name": "SYNTHETIC LOOKUP"}
    )
    response = c.get("/api/staff/patients?local_identifier=SYN-LOOKUP")
    assert response.status_code == 200
    assert len(response.json()) == 1
    with Session(env["engine"]) as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.action == "patient.lookup"))
        assert str(event.patient_id) == created.json()["id"]
        assert str(event.actor_id) == env["ids"]["staff"]
        assert event.request_id == response.headers["x-request-id"]
