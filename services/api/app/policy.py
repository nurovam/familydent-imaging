from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from .common import Context, audit
from .models import Assignment, Clinic, Membership, Study, User


def doctor_scope(user_id: UUID):
    return exists(
        select(Assignment.id)
        .join(
            Membership,
            (Membership.user_id == Assignment.doctor_id) & (Membership.clinic_id == Assignment.clinic_id),
        )
        .join(Clinic, Clinic.id == Assignment.clinic_id)
        .join(User, User.id == Assignment.doctor_id)
        .where(
            Assignment.study_id == Study.id,
            Assignment.doctor_id == user_id,
            Assignment.revoked_at.is_(None),
            Membership.active.is_(True),
            Clinic.active.is_(True),
            User.active.is_(True),
            User.role == "doctor",
        )
    )


def authorize_study(db: Session, request: Request, ctx: Context, study_id: UUID) -> Study:
    if ctx.user.role != "doctor":
        raise HTTPException(403, "FORBIDDEN")
    study = db.scalar(
        select(Study).where(Study.id == study_id, doctor_scope(ctx.user.id), Study.state != "BLOCKED")
    )
    if not study:
        audit(db, request, "study.access_denied", actor=ctx.user.id, result="denied")
        db.commit()
        raise HTTPException(404, "STUDY_UNAVAILABLE")
    return study
