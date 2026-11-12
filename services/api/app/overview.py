"""Minimal cabinet context, never a general audit reader or patient-history API."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from .common import Context, audit, authenticated, database, require_role
from .models import AuditEvent, Patient, Study
from .policy import doctor_scope
from .schemas import StudySummary
from .studies import summary

router = APIRouter(tags=["workspace"])
KINDS = {
    "study.registered": "registered",
    "assignment.created": "assigned",
    "assignment.revoked": "revoked",
    "import.published": "published",
    "study.view": "viewed",
    "imaging.open": "opened",
    "download.started": "downloaded",
}


class WorkspaceEvent(BaseModel):
    id: str
    kind: str
    created_at: str
    study: StudySummary


class Overview(BaseModel):
    latest: StudySummary | None
    events: list[WorkspaceEvent]


@router.get("/api/workspace/overview", response_model=Overview)
def overview(
    request: Request, ctx: Context = Depends(authenticated), db: Session = Depends(database, scope="function")
):
    require_role(ctx, "doctor", "imaging_staff")
    scope = [Study.state != "BLOCKED"]
    if ctx.user.role == "doctor":
        scope.append(doctor_scope(ctx.user.id))
    latest = db.execute(
        select(Study, Patient)
        .join(Patient)
        .where(*scope)
        .order_by(Study.created_at.desc(), Study.id)
        .limit(1)
    ).first()
    events_query = (
        select(AuditEvent, Study, Patient)
        .join(Study, Study.id == AuditEvent.study_id)
        .join(Patient, Patient.id == Study.patient_id)
        .where(*scope, AuditEvent.action.in_(KINDS), AuditEvent.result == "success")
    )
    if ctx.user.role == "doctor":
        events_query = events_query.where(
            or_(
                AuditEvent.action.in_(["study.registered", "import.published"]),
                and_(AuditEvent.action == "assignment.created", AuditEvent.target_user_id == ctx.user.id),
                and_(
                    AuditEvent.action.in_(["study.view", "imaging.open", "download.started"]),
                    AuditEvent.actor_id == ctx.user.id,
                ),
            )
        )
    rows = db.execute(events_query.order_by(AuditEvent.created_at.desc(), AuditEvent.id).limit(3)).all()
    audit(db, request, "workspace.overview", actor=ctx.user.id)
    return {
        "latest": summary(*latest) if latest else None,
        "events": [
            {
                "id": str(event.id),
                "kind": KINDS[event.action],
                "created_at": event.created_at.isoformat(),
                "study": summary(study, patient),
            }
            for event, study, patient in rows
        ],
    }
