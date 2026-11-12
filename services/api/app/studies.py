from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .common import Context, audit, authenticated, database, mutation, require_role
from .models import Assignment, Clinic, Membership, Patient, Study, User
from .policy import authorize_study, doctor_scope
from .schemas import AssignmentInput, PatientInput, StudyInput, StudyPage, StudySummary

router = APIRouter(tags=["studies"])


def summary(study: Study, patient: Patient):
    return {
        "id": str(study.id),
        "patient_id": str(patient.id),
        "local_identifier": patient.local_identifier,
        "display_name": patient.display_name,
        "title": study.title,
        "modality": study.modality,
        "state": study.state,
        "created_at": study.created_at.isoformat(),
    }


@router.get("/api/doctor/studies", response_model=StudyPage)
def doctor_studies(
    request: Request,
    q: str = Query("", max_length=160),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: Context = Depends(authenticated),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "doctor")
    query = select(Study, Patient).join(Patient).where(doctor_scope(ctx.user.id), Study.state != "BLOCKED")
    if q.strip():
        needle = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            Patient.display_name.ilike("%" + needle + "%", escape="\\")
            | Patient.local_identifier.ilike("%" + needle + "%", escape="\\")
        )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.execute(query.order_by(Study.created_at.desc(), Study.id).limit(limit).offset(offset)).all()
    audit(db, request, "study.list", actor=ctx.user.id)
    return {
        "items": [summary(study, patient) for study, patient in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/api/doctor/studies/{study_id}", response_model=StudySummary)
def study_detail(
    study_id: UUID,
    request: Request,
    ctx: Context = Depends(authenticated),
    db: Session = Depends(database, scope="function"),
):
    study = authorize_study(db, request, ctx, study_id)
    patient = db.get(Patient, study.patient_id)
    assert patient is not None
    audit(db, request, "study.view", actor=ctx.user.id, study=study.id)
    return summary(study, patient)


@router.post("/api/staff/patients", status_code=201)
def register_patient(
    data: PatientInput,
    request: Request,
    ctx: Context = Depends(mutation),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "imaging_staff")
    patient = Patient(**data.model_dump())
    db.add(patient)
    db.flush()
    audit(db, request, "patient.registered", actor=ctx.user.id, patient=patient.id)
    return {"id": str(patient.id)}


@router.post("/api/staff/studies", status_code=201)
def register_study(
    data: StudyInput,
    request: Request,
    ctx: Context = Depends(mutation),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "imaging_staff")
    if not db.get(Patient, data.patient_id):
        raise HTTPException(404, "PATIENT_UNAVAILABLE")
    study = Study(**data.model_dump(), created_at=request.app.state.now())
    db.add(study)
    db.flush()
    audit(db, request, "study.registered", actor=ctx.user.id, study=study.id)
    return {"id": str(study.id), "state": study.state}


@router.get("/api/staff/studies", response_model=StudyPage)
def staff_studies(
    request: Request,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: Context = Depends(authenticated),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "imaging_staff")
    rows = db.execute(
        select(Study, Patient)
        .join(Patient)
        .order_by(Study.created_at.desc(), Study.id)
        .limit(limit)
        .offset(offset)
    ).all()
    audit(db, request, "study.staff_list", actor=ctx.user.id)
    return {
        "items": [summary(study, patient) for study, patient in rows],
        "total": db.scalar(select(func.count()).select_from(Study)),
        "limit": limit,
        "offset": offset,
    }


@router.post("/api/staff/studies/{study_id}/assignments", status_code=201)
def assign(
    study_id: UUID,
    data: AssignmentInput,
    request: Request,
    ctx: Context = Depends(mutation),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "imaging_staff")
    study = db.get(Study, study_id, with_for_update=True)
    doctor = db.get(User, data.doctor_id)
    clinic = db.get(Clinic, data.clinic_id)
    member = db.get(Membership, (data.doctor_id, data.clinic_id))
    if (
        not study
        or study.state == "BLOCKED"
        or not doctor
        or not doctor.active
        or doctor.role != "doctor"
        or not clinic
        or not clinic.active
        or not member
        or not member.active
    ):
        raise HTTPException(404, "ASSIGNMENT_UNAVAILABLE")
    assignment = db.scalar(
        select(Assignment).where(
            Assignment.study_id == study_id,
            Assignment.doctor_id == data.doctor_id,
            Assignment.clinic_id == data.clinic_id,
        )
    )
    if assignment and assignment.revoked_at is None:
        raise HTTPException(409, "ALREADY_ASSIGNED")
    if assignment:
        assignment.revoked_at = None
        assignment.created_by, assignment.created_at = ctx.user.id, request.app.state.now()
    else:
        assignment = Assignment(
            study_id=study_id, **data.model_dump(), created_by=ctx.user.id, created_at=request.app.state.now()
        )
        db.add(assignment)
    db.flush()
    audit(
        db,
        request,
        "assignment.created",
        actor=ctx.user.id,
        study=study_id,
        subject=data.doctor_id,
        clinic=data.clinic_id,
        assignment=assignment.id,
    )
    return {"id": str(assignment.id)}


@router.post("/api/staff/assignments/{assignment_id}/revoke", status_code=204)
def revoke_assignment(
    assignment_id: UUID,
    request: Request,
    ctx: Context = Depends(mutation),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "imaging_staff")
    assignment = db.get(Assignment, assignment_id, with_for_update=True)
    if not assignment:
        raise HTTPException(404, "ASSIGNMENT_UNAVAILABLE")
    assignment.revoked_at = request.app.state.now()
    audit(
        db,
        request,
        "assignment.revoked",
        actor=ctx.user.id,
        study=assignment.study_id,
        subject=assignment.doctor_id,
        clinic=assignment.clinic_id,
        assignment=assignment.id,
    )


@router.get("/api/staff/studies/{study_id}/assignments")
def study_assignments(
    study_id: UUID, ctx: Context = Depends(authenticated), db: Session = Depends(database, scope="function")
):
    require_role(ctx, "imaging_staff")
    rows = db.execute(
        select(Assignment, User)
        .join(User, User.id == Assignment.doctor_id)
        .where(Assignment.study_id == study_id)
        .order_by(Assignment.created_at.desc())
    ).all()
    return [{"id": str(a.id), "doctor": u.display_name, "revoked": a.revoked_at is not None} for a, u in rows]


@router.get("/api/staff/patients")
def find_patient(
    request: Request,
    local_identifier: str = Query(min_length=1, max_length=80),
    ctx: Context = Depends(authenticated),
    db: Session = Depends(database),
):
    require_role(ctx, "imaging_staff")
    patient = db.scalar(select(Patient).where(Patient.local_identifier == local_identifier.strip()))
    audit(db, request, "patient.lookup", actor=ctx.user.id, patient=patient.id if patient else None)
    return (
        []
        if not patient
        else [
            {
                "id": str(patient.id),
                "local_identifier": patient.local_identifier,
                "display_name": patient.display_name,
            }
        ]
    )
