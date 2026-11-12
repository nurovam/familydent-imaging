from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Entity:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class Clinic(Entity, Base):
    __tablename__ = "clinics"
    name: Mapped[str] = mapped_column(String(160))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Entity, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('doctor','imaging_staff','platform_admin')", name="user_role"),
    )
    email: Mapped[str] = mapped_column(String(254), unique=True)
    display_name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    totp_secret: Mapped[str | None] = mapped_column(Text)
    last_totp_counter: Mapped[int] = mapped_column(default=-1)


class Membership(Base):
    __tablename__ = "memberships"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    clinic_id: Mapped[UUID] = mapped_column(ForeignKey("clinics.id"), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Patient(Entity, Base):
    __tablename__ = "patients"
    local_identifier: Mapped[str] = mapped_column(String(80), unique=True)
    display_name: Mapped[str] = mapped_column(String(160))


class Study(Entity, Base):
    __tablename__ = "studies"
    __table_args__ = (CheckConstraint("state IN ('REGISTERED','READY','BLOCKED')", name="study_state"),)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    modality: Mapped[str] = mapped_column(String(16))
    dicom_uid: Mapped[str | None] = mapped_column(String(64), unique=True)
    state: Mapped[str] = mapped_column(String(20), default="REGISTERED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Assignment(Entity, Base):
    __tablename__ = "assignments"
    __table_args__ = (UniqueConstraint("study_id", "doctor_id", "clinic_id", name="assignment_scope"),)
    study_id: Mapped[UUID] = mapped_column(ForeignKey("studies.id"), index=True)
    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    clinic_id: Mapped[UUID] = mapped_column(ForeignKey("clinics.id"))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthChallenge(Base):
    __tablename__ = "auth_challenges"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pending_secret: Mapped[str | None] = mapped_column(Text)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthThrottle(Base):
    __tablename__ = "auth_throttles"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class AuditEvent(Entity, Base):
    __tablename__ = "audit_events"
    target_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    target_clinic_id: Mapped[UUID | None] = mapped_column(ForeignKey("clinics.id"))
    assignment_id: Mapped[UUID | None] = mapped_column(ForeignKey("assignments.id"))
    patient_id: Mapped[UUID | None] = mapped_column(ForeignKey("patients.id"))
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    study_id: Mapped[UUID | None] = mapped_column(ForeignKey("studies.id"))
    action: Mapped[str] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(16))
    request_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
