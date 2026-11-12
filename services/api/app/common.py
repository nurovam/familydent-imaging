import hmac
from dataclasses import dataclass
from datetime import timedelta
from typing import NoReturn
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .models import AuditEvent, AuthSession, AuthThrottle, User
from .security import digest


def database(request: Request):
    with Session(request.app.state.engine) as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


def audit(
    db: Session,
    request: Request,
    action: str,
    *,
    actor: UUID | None = None,
    study: UUID | None = None,
    result: str = "success",
    subject: UUID | None = None,
    clinic: UUID | None = None,
    assignment: UUID | None = None,
    patient: UUID | None = None,
):
    db.add(
        AuditEvent(
            actor_id=actor,
            target_user_id=subject,
            target_clinic_id=clinic,
            assignment_id=assignment,
            patient_id=patient,
            study_id=study,
            action=action,
            result=result,
            request_id=request.state.request_id,
            created_at=request.app.state.now(),
        )
    )


def deny(
    db: Session,
    request: Request,
    code: str = "INVALID_CREDENTIALS",
    status: int = 401,
    *,
    actor: UUID | None = None,
    action: str = "auth.failed",
) -> NoReturn:
    audit(db, request, action, actor=actor, result="denied")
    db.commit()  # Keep failed attempts and audit even though HTTPException rolls back dependencies.
    raise HTTPException(status, code)


def throttle(db: Session, request: Request, scope: str, value: str, maximum: int):
    key = digest(value, request.app.state.settings, scope)
    now = request.app.state.now()
    db.execute(insert(AuthThrottle).values(key=key, started_at=now, attempts=0).on_conflict_do_nothing())
    record = db.get(AuthThrottle, key, with_for_update=True)
    assert record is not None
    if now - record.started_at >= timedelta(minutes=15):
        record.started_at, record.attempts = now, 0
    if record.attempts >= maximum:
        deny(db, request, "RATE_LIMITED", 429, action="auth.rate_limited")
    record.attempts += 1
    return record


@dataclass
class Context:
    user: User
    session: AuthSession
    token: str


def authenticated(request: Request, db: Session = Depends(database, scope="function")) -> Context:
    token = request.cookies.get("fd_session", "")
    hashed = digest(token, request.app.state.settings, "session")
    session = db.get(AuthSession, hashed, with_for_update=True)
    now = request.app.state.now()
    user = db.get(User, session.user_id) if session else None
    if (
        not session
        or session.revoked_at
        or not user
        or not user.active
        or not user.totp_secret
        or now - session.last_seen_at >= timedelta(minutes=30)
        or now - session.created_at >= timedelta(hours=8)
    ):
        deny(db, request, "AUTH_REQUIRED", actor=user.id if user else None)
    session.last_seen_at = now
    return Context(user, session, token)


def mutation(request: Request, ctx: Context = Depends(authenticated)) -> Context:
    expected = digest(ctx.token, request.app.state.settings, "csrf")
    if not hmac.compare_digest(expected, request.headers.get("x-csrf-token", "")):
        raise HTTPException(403, "CSRF_FAILED")
    return ctx


def require_role(ctx: Context, *roles: str):
    if ctx.user.role not in roles:
        raise HTTPException(403, "FORBIDDEN")


def lock_account(db: Session, user_id: UUID) -> User | None:
    # PostgreSQL NO KEY UPDATE keeps account/TOTP changes serialized without
    # blocking audit's KEY SHARE references to the unchanged account primary key.
    return db.get(User, user_id, with_for_update={"key_share": True}, populate_existing=True)
