"""Additive, deterministic synthetic metadata; never resets accounts or permissions."""

from datetime import datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Assignment, AuditEvent, Clinic, Membership, Patient, Study, User


def demo_id(kind: str, number: int) -> UUID:
    return uuid5(NAMESPACE_URL, f"familydent:synthetic-demo:{kind}:{number}")


def seed_demo_studies(db: Session, now: datetime) -> dict[str, int]:
    users = {}
    for name, role in [("staff", "imaging_staff"), ("doctor", "doctor"), ("other", "doctor")]:
        user = db.scalar(select(User).where(User.email == name + "@example.test"))
        if not user or user.role != role or not user.active or not user.display_name.startswith("SYNTHETIC "):
            raise ValueError("Requires active synthetic demo accounts; no accounts are created or reset")
        users[name] = user
    memberships = {}
    for name in ("doctor", "other"):
        member = db.scalar(
            select(Membership)
            .join(Clinic)
            .where(Membership.user_id == users[name].id, Membership.active.is_(True), Clinic.active.is_(True))
            .order_by(Membership.clinic_id)
        )
        if not member:
            raise ValueError("Requires existing active synthetic doctor membership")
        memberships[name] = member
    stats = {"patients_created": 0, "studies_created": 0, "assignments_created": 0}
    request_id = str(uuid4())

    def record(action, *, patient=None, study=None, assignment=None):
        db.add(
            AuditEvent(
                action=action,
                result="success",
                actor_id=users["staff"].id,
                patient_id=patient.id if patient else None,
                study_id=study.id if study else None,
                assignment_id=assignment.id if assignment else None,
                target_user_id=assignment.doctor_id if assignment else None,
                target_clinic_id=assignment.clinic_id if assignment else None,
                request_id=request_id,
                created_at=now,
            )
        )

    patients = []
    for n in range(1, 9):
        identifier = f"SYN-DEMO-{n:03d}"
        patient = db.get(Patient, demo_id("patient", n))
        if patient is None:
            if db.scalar(select(Patient).where(Patient.local_identifier == identifier)):
                raise ValueError("Reserved synthetic patient identifier already belongs to another record")
            patient = Patient(
                id=demo_id("patient", n),
                local_identifier=identifier,
                display_name=f"Тестовый пациент {n:02d} (синтетика)",
            )
            db.add(patient)
            db.flush()
            record("demo.patient_created", patient=patient)
            stats["patients_created"] += 1
        elif patient.local_identifier != identifier:
            raise ValueError("Synthetic fixture identity conflict; existing data were not overwritten")
        patients.append(patient)
    titles = [("CBCT", "КЛКТ обеих челюстей"), ("OPG", "Панорамный снимок"), ("IO", "Прицельный снимок")]
    for n in range(1, 13):
        patient = patients[(n - 1) % 8]
        modality, title = titles[(n - 1) % 3]
        study = db.get(Study, demo_id("study", n))
        if study is None:
            study = Study(
                id=demo_id("study", n),
                patient_id=patient.id,
                modality=modality,
                title=f"Тест {n:02d} · {title}",
                state="BLOCKED" if n == 6 else "REGISTERED",
                created_at=now - timedelta(days=n - 1),
            )
            db.add(study)
            db.flush()
            record("demo.study_created", patient=patient, study=study)
            stats["studies_created"] += 1
        elif study.patient_id != patient.id:
            raise ValueError("Synthetic study binding conflict; existing data were not overwritten")
        if n in (10, 11):
            continue  # Unassigned studies are visible only to staff.
        name = "other" if n in (7, 8, 9) else "doctor"
        doctor = users[name]
        member = memberships[name]
        assignment = db.scalar(
            select(Assignment).where(
                Assignment.study_id == study.id,
                Assignment.doctor_id == doctor.id,
                Assignment.clinic_id == member.clinic_id,
            )
        )
        if assignment is None:
            assignment = Assignment(
                study_id=study.id,
                doctor_id=doctor.id,
                clinic_id=member.clinic_id,
                created_by=users["staff"].id,
                created_at=now,
                revoked_at=now if n == 12 else None,
            )
            db.add(assignment)
            db.flush()
            record("demo.assignment_created", study=study, assignment=assignment)
            stats["assignments_created"] += 1
        # Preserve revocation and study state when seeding again.
    return stats
