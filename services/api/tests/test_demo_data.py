from datetime import timedelta

from conftest import login
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.demo_data import seed_demo_studies
from app.models import Assignment, AuthSession, Patient, Study, User


def test_synthetic_seed_is_idempotent_scoped_and_preserves_access_changes(env):
    with Session(env["engine"]) as db, db.begin():
        first = seed_demo_studies(db, env["clock"][0])
        assert first == {"patients_created": 8, "studies_created": 12, "assignments_created": 10}
    c = env["client"]
    login(env, "doctor")
    assert c.get("/api/doctor/studies").json()["total"] == 5
    tokens = dict(c.cookies)
    with Session(env["engine"]) as db, db.begin():
        user = db.scalar(select(User).where(User.email == "doctor@example.test"))
        user_id = user.id
        encrypted_totp = user.totp_secret
        assignment = db.scalar(
            select(Assignment).where(Assignment.doctor_id == user.id, Assignment.revoked_at.is_(None))
        )
        assignment_id = assignment.id
        assignment.revoked_at = env["clock"][0]
        before_sessions = db.scalar(select(func.count()).select_from(AuthSession))
    with Session(env["engine"]) as db, db.begin():
        again = seed_demo_studies(db, env["clock"][0] + timedelta(days=1))
        assert again == {"patients_created": 0, "studies_created": 0, "assignments_created": 0}
        assert db.scalar(select(func.count()).select_from(Patient)) == 8
        assert db.scalar(select(func.count()).select_from(Study)) == 12
        assert db.scalar(select(func.count()).select_from(AuthSession)) == before_sessions
        assert db.get(User, user_id).totp_secret == encrypted_totp
        assert db.get(Assignment, assignment_id).revoked_at == env["clock"][0]
    assert dict(c.cookies) == tokens
    login(env, "other")
    assert c.get("/api/doctor/studies").json()["total"] == 3
    login(env, "staff")
    assert c.get("/api/staff/studies").json()["total"] == 12
