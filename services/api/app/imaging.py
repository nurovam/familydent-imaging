"""Real MFA sessions, per-study assignments, no arbitrary upstream proxying."""

import re
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .common import Context, audit, authenticated, database
from .dicom_validation import valid_uid
from .imaging_storage import checksum, job_path, storage
from .models import AuthSession, DicomImportJob, DicomInstance, Study, User
from .policy import authorize_study, doctor_scope

router = APIRouter(tags=["protected imaging"])


def ready(db: Session, request: Request, ctx: Context, study_id: UUID) -> Study:
    storage(request.app.state.settings)
    study = authorize_study(db, request, ctx, study_id)
    if study.state != "READY" or not db.scalar(
        select(DicomImportJob.id).where(
            DicomImportJob.study_id == study.id, DicomImportJob.state == "PUBLISHED"
        )
    ):
        raise HTTPException(404, "STUDY_UNAVAILABLE")
    return study


def still_allowed(request: Request, user_id: UUID, session_hash: str, study_id: UUID) -> bool:
    now = request.app.state.now()
    with Session(request.app.state.engine) as check:
        return bool(
            check.scalar(
                select(Study.id).where(Study.id == study_id, Study.state == "READY", doctor_scope(user_id))
            )
        ) and bool(
            check.scalar(
                select(AuthSession.token_hash)
                .join(User, User.id == AuthSession.user_id)
                .where(
                    AuthSession.token_hash == session_hash,
                    AuthSession.user_id == user_id,
                    AuthSession.revoked_at.is_(None),
                    User.active.is_(True),
                    User.totp_secret.is_not(None),
                    AuthSession.last_seen_at > now - timedelta(minutes=30),
                    AuthSession.created_at > now - timedelta(hours=8),
                )
            )
        )


def enforce_fresh(request: Request, ctx: Context, study_id: UUID):
    if not still_allowed(request, ctx.user.id, ctx.session.token_hash, study_id):
        raise HTTPException(404, "STUDY_UNAVAILABLE")


def completed(request: Request, user_id: UUID, study_id: UUID, result: str):
    with Session(request.app.state.engine) as db, db.begin():
        audit(db, request, "download.finished", actor=user_id, study=study_id, result=result)


def byte_range(value: str | None, size: int) -> tuple[int, int, int]:
    if value is None:
        return 0, size - 1, 200
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", value)
    if len(value) > 128 or not match or not any(match.groups()):
        raise HTTPException(416, "RANGE_UNSATISFIABLE", headers={"Content-Range": f"bytes */{size}"})
    first, last = match.groups()
    start = int(first) if first else max(0, size - int(last))
    end = min(int(last), size - 1) if first and last else size - 1
    if (not first and int(last) == 0) or start > end or start >= size:
        raise HTTPException(416, "RANGE_UNSATISFIABLE", headers={"Content-Range": f"bytes */{size}"})
    return start, end, 206


def file_response(
    path: Path, sha256: str, size: int, name: str, request: Request, ctx: Context, study_id: UUID, db: Session
):
    if not path.is_file() or path.stat().st_size != size or checksum(path) != sha256:
        raise HTTPException(503, "ORIGINAL_UNAVAILABLE")
    enforce_fresh(request, ctx, study_id)
    range_header = request.headers.get("range")
    if request.headers.get("if-range") not in {None, '"' + sha256 + '"'}:
        range_header = None
    start, end, status = byte_range(range_header, size)
    headers = {
        "Content-Disposition": f'attachment; filename="{name}"',
        "Accept-Ranges": "bytes",
        "ETag": '"' + sha256 + '"',
        "Content-Length": str(end - start + 1),
        "X-Checksum-SHA256": sha256,
    }
    if status == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    audit(db, request, "download.started", actor=ctx.user.id, study=study_id)
    if request.method == "HEAD":
        return Response(headers=headers, status_code=status)

    user_id, session_hash = ctx.user.id, ctx.session.token_hash

    def chunks():
        finished = False
        try:
            with path.open("rb") as source:
                source.seek(start)
                remaining = end - start + 1
                while remaining:
                    if not still_allowed(request, user_id, session_hash, study_id):
                        return
                    data = source.read(min(64 * 1024, remaining))
                    if not data:
                        return
                    remaining -= len(data)
                    yield data
                finished = True
        finally:
            completed(request, user_id, study_id, "success" if finished else "aborted")

    return StreamingResponse(
        chunks(),
        status_code=status,
        headers=headers,
        media_type="application/zip" if name.endswith(".zip") else "application/dicom",
    )


@router.get("/api/doctor/studies/{study_id}/imaging")
def images(
    study_id: UUID,
    request: Request,
    ctx: Context = Depends(authenticated),
    db: Session = Depends(database, scope="function"),
):
    study = ready(db, request, ctx, study_id)
    audit(db, request, "imaging.open", actor=ctx.user.id, study=study_id)
    return {
        "viewer_url": request.app.state.settings.viewer_origin
        + "/viewer?StudyInstanceUIDs="
        + str(study.dicom_uid),
        "zip_url": f"/api/doctor/studies/{study_id}/originals",
        "instances": [
            {
                "id": str(i.id),
                "size": i.size,
                "sha256": i.sha256,
                "url": f"/api/doctor/studies/{study_id}/instances/{i.id}/original",
            }
            for i in db.scalars(
                select(DicomInstance)
                .where(DicomInstance.study_id == study_id)
                .order_by(DicomInstance.sop_uid)
            )
        ],
    }


@router.head("/api/doctor/studies/{study_id}/originals", include_in_schema=False)
@router.get("/api/doctor/studies/{study_id}/originals")
def download_zip(
    study_id: UUID,
    request: Request,
    ctx: Context = Depends(authenticated),
    db: Session = Depends(database, scope="function"),
):
    ready(db, request, ctx, study_id)
    job = db.scalar(
        select(DicomImportJob).where(DicomImportJob.study_id == study_id, DicomImportJob.state == "PUBLISHED")
    )
    assert job and job.zip_sha256 and job.zip_size
    return file_response(
        job_path(request.app.state.settings, job.id) / "originals.bin",
        job.zip_sha256,
        job.zip_size,
        "study-dicom.zip",
        request,
        ctx,
        study_id,
        db,
    )


@router.head("/api/doctor/studies/{study_id}/instances/{instance_id}/original", include_in_schema=False)
@router.get("/api/doctor/studies/{study_id}/instances/{instance_id}/original")
def download_instance(
    study_id: UUID,
    instance_id: UUID,
    request: Request,
    ctx: Context = Depends(authenticated),
    db: Session = Depends(database, scope="function"),
):
    ready(db, request, ctx, study_id)
    instance = db.scalar(
        select(DicomInstance).where(DicomInstance.id == instance_id, DicomInstance.study_id == study_id)
    )
    if not instance:
        raise HTTPException(404, "INSTANCE_UNAVAILABLE")
    return file_response(
        job_path(request.app.state.settings, instance.job_id) / f"{instance.id}.bin",
        instance.sha256,
        instance.size,
        "instance.dcm",
        request,
        ctx,
        study_id,
        db,
    )


def remove_bulk(value):
    if isinstance(value, list):
        return [remove_bulk(item) for item in value]
    if isinstance(value, dict):
        return {key: remove_bulk(item) for key, item in value.items() if key != "BulkDataURI"}
    return value


def tag(item: dict, key: str) -> str:
    return str(item.get(key, {}).get("Value", [""])[0])


@router.head("/api/imaging/dicom-web/{path:path}", include_in_schema=False)
@router.get("/api/imaging/dicom-web/{path:path}")
def dicomweb(
    path: str,
    request: Request,
    ctx: Context = Depends(authenticated),
    db: Session = Depends(database, scope="function"),
):
    storage(request.app.state.settings)
    if ctx.user.role != "doctor":
        raise HTTPException(403, "FORBIDDEN")
    query = list(request.query_params.multi_items())
    allowed = {"StudyInstanceUID", "includefield", "limit", "offset", "fuzzymatching"}
    if (
        len(query) > 12
        or any(k not in allowed or len(v) > 128 for k, v in query)
        or "range" in request.headers
    ):
        raise HTTPException(400, "UNSUPPORTED_DICOM_QUERY")
    parts = path.split("/")
    if path == "studies":
        supplied = request.query_params.getlist("StudyInstanceUID")
        uid = supplied[0] if len(supplied) == 1 else ""
    else:
        uid = parts[1] if len(parts) >= 2 and parts[0] == "studies" else ""
    if not valid_uid(uid):
        raise HTTPException(404, "STUDY_UNAVAILABLE")
    sid = db.scalar(select(Study.id).where(Study.dicom_uid == uid))
    if not sid:
        raise HTTPException(404, "STUDY_UNAVAILABLE")
    study = ready(db, request, ctx, sid)
    instances = list(db.scalars(select(DicomInstance).where(DicomInstance.study_id == sid)))
    series = {i.series_uid for i in instances}
    sops = {i.sop_uid for i in instances}
    root = f"studies/{uid}"
    paths = {"studies", root + "/metadata", root + "/series", root + "/instances"}
    for s in series:
        paths.update({root + f"/series/{s}/metadata", root + f"/series/{s}/instances"})
    for i in instances:
        base = root + f"/series/{i.series_uid}/instances/{i.sop_uid}"
        paths.update({base + "/metadata", base + "/frames/1"})
    if path not in paths or (
        path != "studies" and request.query_params.getlist("StudyInstanceUID") not in ([], [uid])
    ):
        raise HTTPException(404, "STUDY_UNAVAILABLE")
    try:
        with httpx.Client(
            base_url=request.app.state.settings.orthanc_url,
            trust_env=False,
            timeout=20,
            follow_redirects=False,
        ) as client:
            with client.stream(
                request.method,
                "/dicom-web/" + path,
                params=httpx.QueryParams(tuple(query)),
                headers={"Accept": request.headers.get("accept", "application/dicom+json")},
            ) as upstream:
                if upstream.status_code != 200:
                    raise HTTPException(502, "ARCHIVE_UNAVAILABLE")
                data = bytearray()
                for chunk in upstream.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 32 * 1024 * 1024:
                        raise HTTPException(502, "ARCHIVE_LIMIT")
                content_type = upstream.headers.get("content-type", "application/octet-stream")
        enforce_fresh(request, ctx, sid)
        audit(db, request, "dicom.read", actor=ctx.user.id, study=study.id)
        if request.method == "HEAD":
            return Response(media_type=content_type)
        if "json" in content_type:
            import json

            items = json.loads(data)
            if not isinstance(items, list):
                raise ValueError()
            filtered = [
                item
                for item in items
                if tag(item, "0020000D") in {"", uid}
                and tag(item, "0020000E") in {"", *series}
                and tag(item, "00080018") in {"", *sops}
            ]
            return JSONResponse(remove_bulk(filtered), media_type="application/dicom+json")
        return Response(bytes(data), media_type=content_type)
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        raise HTTPException(502, "ARCHIVE_UNAVAILABLE") from None
