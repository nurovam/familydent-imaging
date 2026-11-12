from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .common import Context, audit, authenticated, database, lock_account, mutation, require_role
from .models import Assignment, AuthChallenge, AuthSession, Clinic, Membership, User
from .schemas import ClinicInput, UserInput
from .security import hash_password

router = APIRouter(tags=["account management"])


@router.post("/api/admin/clinics", status_code=201)
def create_clinic(
    data: ClinicInput,
    request: Request,
    ctx: Context = Depends(mutation),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "platform_admin")
    clinic = Clinic(name=data.name)
    db.add(clinic)
    db.flush()
    audit(db, request, "clinic.created", actor=ctx.user.id, clinic=clinic.id)
    return {"id": str(clinic.id), "name": clinic.name}


@router.get("/api/clinics")
def clinics(ctx: Context = Depends(authenticated), db: Session = Depends(database, scope="function")):
    require_role(ctx, "platform_admin", "imaging_staff")
    return [
        {"id": str(c.id), "name": c.name} for c in db.scalars(select(Clinic).where(Clinic.active.is_(True)))
    ]


@router.post("/api/admin/users", status_code=201)
def create_user(
    data: UserInput,
    request: Request,
    ctx: Context = Depends(mutation),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "platform_admin", "imaging_staff")
    if ctx.user.role == "imaging_staff" and data.role != "doctor":
        raise HTTPException(403, "FORBIDDEN")
    clinic = db.get(Clinic, data.clinic_id) if data.clinic_id else None
    if data.role == "doctor" and (not clinic or not clinic.active):
        raise HTTPException(422, "CLINIC_REQUIRED")
    user = User(
        email=data.email,
        display_name=data.display_name,
        role=data.role,
        password_hash=hash_password(data.password.get_secret_value()),
    )
    db.add(user)
    db.flush()
    if data.role == "doctor":
        db.add(Membership(user_id=user.id, clinic_id=data.clinic_id))
    audit(db, request, "account.created", actor=ctx.user.id, subject=user.id)
    return {"id": str(user.id), "role": user.role}


@router.get("/api/staff/doctors")
def doctors(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: Context = Depends(authenticated),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "platform_admin", "imaging_staff")
    rows = db.execute(
        select(User, Membership)
        .join(Membership)
        .join(Clinic)
        .where(
            User.role == "doctor", User.active.is_(True), Membership.active.is_(True), Clinic.active.is_(True)
        )
        .order_by(User.email, Membership.clinic_id)
        .limit(limit)
        .offset(offset)
    ).all()
    return [{"id": str(u.id), "display_name": u.display_name, "clinic_id": str(m.clinic_id)} for u, m in rows]


@router.post("/api/admin/users/{user_id}/disable", status_code=204)
def disable(
    user_id: UUID,
    request: Request,
    ctx: Context = Depends(mutation),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "platform_admin")
    if ctx.user.id == user_id:
        raise HTTPException(409, "CANNOT_DISABLE_SELF")
    user = lock_account(db, user_id)
    if not user:
        raise HTTPException(404, "ACCOUNT_UNAVAILABLE")
    now = request.app.state.now()
    user.active = False
    db.execute(update(AuthSession).where(AuthSession.user_id == user_id).values(revoked_at=now))
    db.execute(update(AuthChallenge).where(AuthChallenge.user_id == user_id).values(consumed_at=now))
    db.execute(update(Assignment).where(Assignment.doctor_id == user_id).values(revoked_at=now))
    audit(db, request, "account.disabled", actor=ctx.user.id, subject=user_id)


@router.post("/api/admin/memberships/{user_id}/{clinic_id}/revoke", status_code=204)
def revoke_membership(
    user_id: UUID,
    clinic_id: UUID,
    request: Request,
    ctx: Context = Depends(mutation),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "platform_admin")
    member = db.get(Membership, (user_id, clinic_id), with_for_update=True)
    if not member:
        raise HTTPException(404, "MEMBERSHIP_UNAVAILABLE")
    now = request.app.state.now()
    member.active = False
    db.execute(
        update(Assignment)
        .where(Assignment.doctor_id == user_id, Assignment.clinic_id == clinic_id)
        .values(revoked_at=now)
    )
    audit(db, request, "membership.revoked", actor=ctx.user.id, subject=user_id, clinic=clinic_id)


@router.get("/api/admin/users")
def accounts(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: Context = Depends(authenticated),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "platform_admin")
    return [
        {
            "id": str(u.id),
            "display_name": u.display_name,
            "email": u.email,
            "role": u.role,
            "active": u.active,
        }
        for u in db.scalars(select(User).order_by(User.email).limit(limit).offset(offset))
    ]
