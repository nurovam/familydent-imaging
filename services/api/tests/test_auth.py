from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pyotp
from conftest import login
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuthSession, User


def test_password_is_not_enough_and_enrollment_issues_rotated_cookie(env):
    c = env["client"]
    old = c.cookies.get("fd_session")
    response = c.post(
        "/api/auth/password", json={"email": "doctor@example.test", "password": env["password"]}
    )
    assert response.json()["next"] == "enroll_totp"
    assert c.get("/api/doctor/studies").status_code == 401
    enrollment = c.post("/api/auth/totp/enroll").json()
    assert enrollment["provisioning_uri"].startswith("otpauth://totp/")
    secret = enrollment["secret"]
    response = c.post("/api/auth/totp", json={"code": pyotp.TOTP(secret).at(env["clock"][0])})
    assert response.status_code == 200
    assert c.cookies.get("fd_challenge") is None
    token = c.cookies.get("fd_session")
    assert token and token != old
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert secret not in response.text
    with Session(env["engine"]) as db:
        user = db.scalar(select(User).where(User.email == "doctor@example.test"))
        assert secret not in user.totp_secret
        assert env["password"] not in user.password_hash
        assert db.scalar(select(AuthSession)).token_hash != token


def test_totp_replay_failed_attempts_and_consumed_challenge(env):
    secret = login(env)
    c = env["client"]
    assert c.post("/api/auth/totp", json={"code": pyotp.TOTP(secret).at(env["clock"][0])}).status_code == 401
    c.post("/api/auth/password", json={"email": "doctor@example.test", "password": env["password"]})
    assert c.post("/api/auth/totp/enroll").status_code == 409
    assert c.post("/api/auth/totp", json={"code": pyotp.TOTP(secret).at(env["clock"][0])}).status_code == 401
    wrong = next(
        f"{n:06d}"
        for n in range(100)
        if not pyotp.TOTP(secret).verify(f"{n:06d}", for_time=env["clock"][0], valid_window=1)
    )
    for _ in range(4):
        assert c.post("/api/auth/totp", json={"code": wrong}).status_code == 401
    env["clock"][0] += timedelta(seconds=30)
    assert c.post("/api/auth/totp", json={"code": pyotp.TOTP(secret).at(env["clock"][0])}).status_code in (
        401,
        429,
    )


def test_expired_challenge_and_idle_absolute_logout_csrf(env):
    c = env["client"]
    c.post("/api/auth/password", json={"email": "doctor@example.test", "password": env["password"]})
    secret = c.post("/api/auth/totp/enroll").json()["secret"]
    env["clock"][0] += timedelta(minutes=6)
    assert c.post("/api/auth/totp", json={"code": pyotp.TOTP(secret).at(env["clock"][0])}).status_code == 401
    login(env)
    assert c.post("/api/auth/logout", headers={"Origin": "http://evil"}).status_code == 403
    assert c.post("/api/auth/logout", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert c.get("/api/auth/me").status_code == 200
    env["clock"][0] += timedelta(minutes=31)
    assert c.get("/api/auth/me").status_code == 401
    login(env)
    with Session(env["engine"]) as db, db.begin():
        session = db.scalar(
            select(AuthSession)
            .where(AuthSession.revoked_at.is_(None))
            .order_by(AuthSession.created_at.desc())
        )
        session.created_at = env["clock"][0] - timedelta(hours=9)
    assert c.get("/api/auth/me").status_code == 401
    env["clock"][0] += timedelta(seconds=30)
    login(env)
    assert c.post("/api/auth/logout").status_code == 204
    assert c.get("/api/auth/me").status_code == 401


def test_unknown_and_wrong_password_generic_and_rate_limited(env):
    c = env["client"]
    wrong = c.post("/api/auth/password", json={"email": "doctor@example.test", "password": "wrong"})
    unknown = c.post("/api/auth/password", json={"email": "unknown@example.test", "password": "wrong"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["code"] == unknown.json()["code"] == "INVALID_CREDENTIALS"
    for _ in range(4):
        c.post("/api/auth/password", json={"email": "doctor@example.test", "password": "wrong"})
    assert (
        c.post(
            "/api/auth/password", json={"email": "doctor@example.test", "password": env["password"]}
        ).status_code
        == 429
    )
    env["clock"][0] += timedelta(minutes=16)
    assert (
        c.post(
            "/api/auth/password", json={"email": "doctor@example.test", "password": env["password"]}
        ).status_code
        == 200
    )


def test_same_totp_cannot_be_redeemed_concurrently(env):
    c = env["client"]
    c.post("/api/auth/password", json={"email": "doctor@example.test", "password": env["password"]})
    enrollment = c.post("/api/auth/totp/enroll").json()
    cookie = c.cookies.get("fd_challenge")
    code = pyotp.TOTP(enrollment["secret"]).at(env["clock"][0])

    def submit(_):
        with TestClient(env["app"]) as other:
            other.cookies.set("fd_challenge", cookie)
            return other.post(
                "/api/auth/totp", json={"code": code}, headers={"Origin": "http://testserver"}
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, range(2))) == [200, 401]


def test_disable_can_update_challenge_while_totp_waits_for_user_lock(env):
    import time

    from sqlalchemy import text

    c = env["client"]
    c.post("/api/auth/password", json={"email": "doctor@example.test", "password": env["password"]})
    secret = c.post("/api/auth/totp/enroll").json()["secret"]
    cookie = c.cookies.get("fd_challenge")
    code = pyotp.TOTP(secret).at(env["clock"][0])

    def verify():
        with TestClient(env["app"]) as other:
            other.cookies.set("fd_challenge", cookie)
            return other.post(
                "/api/auth/totp", json={"code": code}, headers={"Origin": "http://testserver"}
            ).status_code

    # Same first lock as disabling: lock user before updating sessions/challenges.
    connection = env["admin_engine"].connect()
    transaction = connection.begin()
    connection.execute(text("SELECT id FROM users WHERE id=:id FOR UPDATE"), {"id": env["ids"]["doctor"]})
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(verify)
        try:
            with env["admin_engine"].connect() as observer:
                for _ in range(100):
                    waiting = observer.scalar(
                        text(
                            "SELECT count(*) FROM pg_stat_activity WHERE datname='familydent_test' AND usename='familydent_app' AND wait_event_type='Lock'"
                        )
                    )
                    if waiting:
                        break
                    time.sleep(0.01)
                else:
                    raise AssertionError("TOTP verification never waited for account lock")
            connection.execute(text("SET LOCAL lock_timeout='500ms'"))
            connection.execute(
                text("UPDATE auth_challenges SET consumed_at=:now WHERE user_id=:id"),
                {"id": env["ids"]["doctor"], "now": env["clock"][0]},
            )
            connection.execute(
                text("UPDATE users SET active=false WHERE id=:id"), {"id": env["ids"]["doctor"]}
            )
            transaction.commit()
        finally:
            if transaction.is_active:
                transaction.rollback()
            connection.close()
        assert future.result(timeout=5) == 401


def test_account_disable_lock_allows_inflight_audit_fk(env):
    # Strong FOR UPDATE on users would block audit's FK KEY SHARE lock and deadlock
    # against an already authenticated request holding its session. NO KEY UPDATE
    # serializes account/TOTP changes while allowing FK references to unchanged IDs.
    from uuid import UUID, uuid4

    from sqlalchemy import text

    login(env)
    with Session(env["engine"]) as auth_db:
        from app.common import lock_account

        account = lock_account(auth_db, UUID(env["ids"]["doctor"]))
        assert account is not None
        with env["engine"].begin() as writer:
            writer.execute(text("SET LOCAL lock_timeout='500ms'"))
            writer.execute(
                text(
                    "INSERT INTO audit_events (id, actor_id, action, result, request_id, created_at) VALUES (:id, :actor, 'study.list', 'success', :request, :now)"
                ),
                {"id": uuid4(), "actor": account.id, "request": str(uuid4()), "now": env["clock"][0]},
            )
