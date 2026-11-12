"""One isolated local worker, bounded child per import; DB queue is durable."""

import argparse
import resource
import subprocess
import sys
import time
import zipfile
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from .config import Settings
from .dicom_validation import InvalidDicom, read_upload
from .imaging_storage import checksum, job_path, write_private
from .models import AuditEvent, DicomImportJob, DicomInstance, Patient, Study
from .runtime import local_settings


def event(db: Session, job: DicomImportJob, action: str, result: str = "success"):
    db.add(
        AuditEvent(
            actor_id=job.created_by,
            study_id=job.study_id,
            action=action,
            result=result,
            request_id=str(uuid4()),
            created_at=datetime.now(UTC),
        )
    )


def process_job(engine, settings: Settings, job_id: UUID):
    with Session(engine) as db, db.begin():
        # Rollback on a process crash leaves QUEUED, and no READY transition is possible.
        job = db.get(DicomImportJob, job_id, with_for_update=True)
        if not job or job.state != "QUEUED":
            return
        study = db.get(Study, job.study_id, with_for_update=True)
        assert study is not None
        patient = db.get(Patient, study.patient_id)
        assert patient is not None
        directory = job_path(settings, job.id)
        created = []
        try:
            if study.state != "REGISTERED":
                raise InvalidDicom("STUDY_NOT_REGISTERED")
            items = read_upload(directory / "upload.bin", job.kind, patient.local_identifier)
            uid = items[0].study_uid
            if study.dicom_uid and study.dicom_uid != uid:
                raise InvalidDicom("STUDY_UID_MISMATCH")
            if db.scalar(select(Study.id).where(Study.dicom_uid == uid, Study.id != study.id)):
                raise InvalidDicom("STUDY_UID_CONFLICT")
            if db.scalar(
                select(DicomInstance.id).where(DicomInstance.sop_uid.in_([i.sop_uid for i in items]))
            ):
                raise InvalidDicom("INSTANCE_UID_CONFLICT")
            # All files have passed validation before any archive call or instance insert.
            # Crash leftovers stay private; a retry may only reuse byte-identical instances.
            with httpx.Client(
                base_url=settings.orthanc_url, timeout=15, trust_env=False, follow_redirects=False
            ) as client:
                for item in items:
                    response = client.post(
                        "/instances", content=item.data, headers={"Content-Type": "application/dicom"}
                    )
                    response.raise_for_status()
                    result = response.json()
                    oid = str(result["ID"])
                    import re

                    if not re.fullmatch(r"[0-9a-f-]{40,64}", oid):
                        raise InvalidDicom("ARCHIVE_FAILED")
                    # Orthanc never overwrites. Detect pre-existing, differing originals.
                    original = client.get(f"/instances/{oid}/file")
                    original.raise_for_status()
                    import hashlib

                    if hashlib.sha256(original.content).hexdigest() != item.sha256:
                        raise InvalidDicom("ARCHIVE_CONFLICT")
                    instance = DicomInstance(
                        id=uuid4(),
                        job_id=job.id,
                        study_id=study.id,
                        series_uid=item.series_uid,
                        sop_uid=item.sop_uid,
                        orthanc_id=oid,
                        sha256=item.sha256,
                        size=len(item.data),
                    )
                    created.append(instance)
                    write_private(directory / f"{instance.id}.bin", item.data)
            # Deterministic archive, originals unchanged; no licensed Viewer or extra files.
            zip_path = directory / "originals.bin"
            zip_path.unlink(missing_ok=True)  # Only an uncommitted generated temporary artifact.
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as archive:
                for instance, item in zip(created, items, strict=True):
                    info = zipfile.ZipInfo(str(instance.id) + ".dcm", date_time=(1980, 1, 1, 0, 0, 0))
                    archive.writestr(info, item.data)
            zip_path.chmod(0o600)
            db.add_all(created)
            # Reserve this UID while awaiting explicit staff review; prevents cross-study races.
            study.dicom_uid = uid
            job.study_uid, job.state = uid, "REVIEW"
            job.zip_sha256, job.zip_size = checksum(zip_path), zip_path.stat().st_size
            event(db, job, "import.validated")
        except (InvalidDicom, httpx.HTTPError, OSError, ValueError, KeyError):
            # No parser/HTTP response body, filenames, or PHI in errors/logs.
            import sys

            error = sys.exception()
            job.state = "FAILED"
            job.error_code = str(error) if isinstance(error, InvalidDicom) else "ARCHIVE_FAILED"
            event(db, job, "import.failed", "failed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--job", type=UUID, help=argparse.SUPPRESS)
    args = parser.parse_args()
    local_settings()
    settings = Settings.from_env()
    engine = create_engine(settings.database_url, hide_parameters=True)
    if args.job:
        # Resource containment supplements file/count/expansion limits, not a sandbox for clinical data.
        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (45, 45))
        process_job(engine, settings, args.job)
        engine.dispose()
        return
    try:
        with engine.connect() as guard:
            if not guard.scalar(text("SELECT pg_try_advisory_lock(736245910)")):
                raise SystemExit("A local imaging worker is already running")
            while True:
                with Session(engine) as db:
                    job_id = db.scalar(
                        select(DicomImportJob.id)
                        .where(DicomImportJob.state == "QUEUED")
                        .order_by(DicomImportJob.created_at)
                        .limit(1)
                    )
                if job_id:
                    try:
                        result = subprocess.run(
                            [sys.executable, "-m", "app.worker", "--job", str(job_id)],
                            timeout=60,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=False,
                        )
                        failed = result.returncode != 0
                    except subprocess.TimeoutExpired:
                        failed = True
                    if failed:
                        with Session(engine) as db, db.begin():
                            job = db.get(DicomImportJob, job_id, with_for_update=True)
                            if job and job.state == "QUEUED":
                                job.state, job.error_code = "FAILED", "WORKER_LIMIT"
                                event(db, job, "import.failed", "failed")
                if args.once:
                    break
                time.sleep(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
