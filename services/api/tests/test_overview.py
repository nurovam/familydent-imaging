from conftest import login
from fastapi.testclient import TestClient
from test_assignments import create_study


def test_overview_uses_real_events_and_immediate_assignment_scope(env):
    c = env["client"]
    login(env, "staff")
    sid = create_study(env)
    aid = c.post(
        f"/api/staff/studies/{sid}/assignments",
        json={"doctor_id": env["ids"]["doctor"], "clinic_id": env["ids"]["clinic"]},
    ).json()["id"]
    with TestClient(env["app"]) as doctor:
        doctor.headers["Origin"] = "http://testserver"
        login({**env, "client": doctor})
        response = doctor.get("/api/workspace/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["latest"]["id"] == sid
        assert {event["kind"] for event in data["events"]} == {"registered", "assigned"}
        assert all(event["study"]["id"] == sid for event in data["events"])
        assert "actor_id" not in response.text and "request_id" not in response.text
        doctor.get(f"/api/doctor/studies/{sid}")
        assert "viewed" in {e["kind"] for e in doctor.get("/api/workspace/overview").json()["events"]}
        c.post(f"/api/staff/assignments/{aid}/revoke")
        assert doctor.get("/api/workspace/overview").json() == {"latest": None, "events": []}
    login(env, "other")
    assert c.get("/api/workspace/overview").json() == {"latest": None, "events": []}
    login(env, "admin")
    assert c.get("/api/workspace/overview").status_code == 403


def test_overview_is_staff_only_or_explicitly_assigned_and_hides_blocked(env):
    from uuid import UUID

    from sqlalchemy.orm import Session

    from app.models import Study

    c = env["client"]
    assert c.get("/api/workspace/overview").status_code == 401
    login(env, "staff")
    sid = create_study(env)
    assert c.get("/api/workspace/overview").json()["latest"]["id"] == sid
    with Session(env["engine"]) as db, db.begin():
        db.get(Study, UUID(sid)).state = "BLOCKED"
    assert c.get("/api/workspace/overview").json() == {"latest": None, "events": []}
