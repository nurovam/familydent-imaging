import uuid

import pytest
from conftest import login
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models import AuditEvent


def create_study(env):
    c = env["client"]
    patient = c.post(
        "/api/staff/patients", json={"local_identifier": "SYNTHETIC-001", "display_name": "SYNTHETIC PATIENT"}
    )
    assert patient.status_code == 201, patient.text
    study = c.post(
        "/api/staff/studies",
        json={"patient_id": patient.json()["id"], "title": "SYNTHETIC STUDY", "modality": "CBCT"},
    )
    assert study.status_code == 201
    return study.json()["id"]


def test_explicit_assignment_scope_and_revoke(env):
    c = env["client"]
    login(env, "staff")
    study_id = create_study(env)
    payload = {"doctor_id": env["ids"]["doctor"], "clinic_id": env["ids"]["clinic"]}
    assignment = c.post(f"/api/staff/studies/{study_id}/assignments", json=payload)
    assert assignment.status_code == 201, assignment.text
    assignment_id = assignment.json()["id"]
    login(env, "other")
    assert c.get("/api/doctor/studies").json()["total"] == 0
    assert c.get(f"/api/doctor/studies/{study_id}").status_code == 404
    assert c.post(f"/api/staff/studies/{study_id}/assignments", json=payload).status_code == 403
    login(env, "doctor")
    assert c.get("/api/doctor/studies", params={"q": "SYNTHETIC-001", "limit": 1}).json()["total"] == 1
    assert c.get("/api/doctor/studies", params={"q": "absent"}).json()["total"] == 0
    assert c.get(f"/api/doctor/studies/{study_id}").status_code == 200
    env["clock"][0] = env["clock"][0].replace(second=30)
    with TestClient(env["app"]) as staff_client:
        staff_client.headers["Origin"] = "http://testserver"
        login({**env, "client": staff_client}, "staff")
        assert staff_client.post(f"/api/staff/assignments/{assignment_id}/revoke").status_code == 204
    assert c.get(f"/api/doctor/studies/{study_id}").status_code == 404
    assert c.get("/api/doctor/studies").json()["total"] == 0
    with Session(env["engine"]) as db:
        assert "assignment.revoked" in db.scalars(select(AuditEvent.action)).all()
        with pytest.raises(DBAPIError):
            db.execute(text("DELETE FROM audit_events"))


def test_admin_is_not_medical_reader_and_deactivation_invalidates_session(env):
    c = env["client"]
    login(env, "doctor")
    with TestClient(env["app"]) as admin_client:
        admin_client.headers["Origin"] = "http://testserver"
        login({**env, "client": admin_client}, "admin")
        assert admin_client.get("/api/doctor/studies").status_code == 403
        assert (
            admin_client.post(
                "/api/staff/patients", json={"local_identifier": "X", "display_name": "X"}
            ).status_code
            == 403
        )
        assert admin_client.post(f"/api/admin/users/{env['ids']['doctor']}/disable").status_code == 204
    assert c.get("/api/auth/me").status_code == 401


def test_metadata_does_not_merge_by_name_and_rejects_duplicate_internal_id(env):
    c = env["client"]
    login(env, "staff")
    a = c.post("/api/staff/patients", json={"local_identifier": "SYN-A", "display_name": "SAME NAME"})
    b = c.post("/api/staff/patients", json={"local_identifier": "SYN-B", "display_name": "SAME NAME"})
    assert a.status_code == b.status_code == 201
    assert a.json()["id"] != b.json()["id"]
    assert (
        c.post("/api/staff/patients", json={"local_identifier": "SYN-A", "display_name": "OTHER"}).status_code
        == 409
    )
    assert (
        c.post(
            "/api/staff/studies", json={"patient_id": str(uuid.uuid4()), "title": "X", "modality": "CBCT"}
        ).status_code
        == 404
    )
    assert (
        c.post(
            "/api/staff/patients", json={"local_identifier": "Y", "display_name": "X", "tenant_id": "other"}
        ).status_code
        == 422
    )


def test_audit_identifies_assignment_targets_and_staff_reads(env):
    c = env["client"]
    login(env, "staff")
    study = create_study(env)
    with Session(env["engine"]) as db:
        before = set(db.scalars(select(AuditEvent.id)))
    page = c.get("/api/staff/studies")
    assert page.status_code == 200
    with Session(env["engine"]) as db:
        reads = db.scalars(
            select(AuditEvent).where(AuditEvent.id.not_in(before), AuditEvent.action == "study.staff_list")
        ).all()
        assert len(reads) == 1
        assert str(reads[0].actor_id) == env["ids"]["staff"]
        assert reads[0].request_id == page.headers["x-request-id"]
    ids = []
    for who in ("doctor", "other"):
        response = c.post(
            f"/api/staff/studies/{study}/assignments",
            json={"doctor_id": env["ids"][who], "clinic_id": env["ids"]["clinic"]},
        )
        assert response.status_code == 201
        ids.append(response.json()["id"])
    c.post(f"/api/staff/assignments/{ids[0]}/revoke")
    c.post(
        f"/api/staff/studies/{study}/assignments",
        json={"doctor_id": env["ids"]["doctor"], "clinic_id": env["ids"]["clinic"]},
    )
    with Session(env["engine"]) as db:
        events = db.scalars(select(AuditEvent).where(AuditEvent.action.like("assignment.%"))).all()
        assert len(events) == 4
        assert all(
            e.assignment_id and e.target_user_id and str(e.target_clinic_id) == env["ids"]["clinic"]
            for e in events
        )
        revoked = next(e for e in events if e.action == "assignment.revoked")
        assert str(revoked.assignment_id) == ids[0]
        assert str(revoked.target_user_id) == env["ids"]["doctor"]
