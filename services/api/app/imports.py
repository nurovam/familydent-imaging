"""Staff uploads remain private until a separate, explicit review."""

import asyncio
import os
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .common import Context, audit, authenticated, database, mutation, require_role, throttle
from .dicom_validation import UPLOAD_LIMIT
from .imaging_storage import job_path, storage
from .models import DicomImportJob, DicomInstance, Study

router = APIRouter(tags=["imaging imports"])


def job_summary(db: Session, job: DicomImportJob):
    return {
        "id": str(job.id),
        "study_id": str(job.study_id),
        "state": job.state,
        "error_code": job.error_code,
        "study_uid": job.study_uid,
        "instances": db.scalar(
            select(func.count()).select_from(DicomInstance).where(DicomInstance.job_id == job.id)
        ),
        "created_at": job.created_at.isoformat(),
    }


@router.post("/api/staff/studies/{study_id}/imports", status_code=202)
async def upload(
    study_id: UUID,
    request: Request,
    ctx: Context = Depends(mutation),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "imaging_staff")
    root = storage(request.app.state.settings)
    kind = {"application/dicom": "dicom", "application/zip": "zip"}.get(
        request.headers.get("content-type", "")
    )
    if not kind:
        raise HTTPException(415, "DICOM_OR_ZIP_REQUIRED")
    throttle(db, request, "import", str(ctx.user.id), 20)
    study = db.get(Study, study_id, with_for_update=True)
    if not study or study.state != "REGISTERED":
        raise HTTPException(409, "STUDY_NOT_REGISTERED")
    if db.scalar(
        select(DicomImportJob.id).where(
            DicomImportJob.study_id == study_id, DicomImportJob.state.in_(["QUEUED", "REVIEW", "PUBLISHED"])
        )
    ):
        raise HTTPException(409, "IMPORT_EXISTS")
    if sum(p.stat().st_size for p in root.glob("*/*.bin")) > 256 * 1024 * 1024:
        raise HTTPException(507, "LOCAL_STORAGE_LIMIT")
    job = DicomImportJob(
        id=uuid4(), study_id=study_id, created_by=ctx.user.id, created_at=request.app.state.now(), kind=kind
    )
    directory = job_path(request.app.state.settings, job.id)
    directory.mkdir(mode=0o700)
    target = directory / "upload.bin"
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as output:
            size = 0
            async with asyncio.timeout(45):
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > UPLOAD_LIMIT:
                        raise HTTPException(413, "UPLOAD_LIMIT")
                    output.write(chunk)
        if not size:
            raise HTTPException(422, "EMPTY_UPLOAD")
        db.add(job)
        db.flush()
        audit(db, request, "import.queued", actor=ctx.user.id, study=study_id)
        return job_summary(db, job)
    except BaseException:
        target.unlink(missing_ok=True)
        directory.rmdir()
        raise


@router.get("/api/staff/studies/{study_id}/imports")
def jobs(
    study_id: UUID,
    request: Request,
    ctx: Context = Depends(authenticated),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "imaging_staff")
    if not db.get(Study, study_id):
        raise HTTPException(404, "STUDY_UNAVAILABLE")
    audit(db, request, "import.list", actor=ctx.user.id, study=study_id)
    return [
        job_summary(db, job)
        for job in db.scalars(
            select(DicomImportJob)
            .where(DicomImportJob.study_id == study_id)
            .order_by(DicomImportJob.created_at.desc())
            .limit(20)
        )
    ]


class ConfirmImport(BaseModel):
    confirmed: bool = Field(strict=True)


@router.post("/api/staff/studies/{study_id}/imports/{job_id}/publish")
def publish(
    study_id: UUID,
    job_id: UUID,
    data: ConfirmImport,
    request: Request,
    ctx: Context = Depends(mutation),
    db: Session = Depends(database, scope="function"),
):
    require_role(ctx, "imaging_staff")
    job = db.get(DicomImportJob, job_id, with_for_update=True)
    if not job or job.study_id != study_id:
        raise HTTPException(404, "IMPORT_UNAVAILABLE")
    study = db.get(Study, study_id, with_for_update=True)
    if (
        not data.confirmed
        or job.state != "REVIEW"
        or not study
        or study.state != "REGISTERED"
        or not job.study_uid
        or study.dicom_uid != job.study_uid
        or not job.zip_sha256
    ):
        raise HTTPException(409, "IMPORT_NOT_REVIEWABLE")
    job.state, study.state = "PUBLISHED", "READY"
    audit(db, request, "import.published", actor=ctx.user.id, study=study.id)
    return {"state": study.state}
