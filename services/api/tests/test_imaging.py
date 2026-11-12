"""Real PostgreSQL + Orthanc: no fake authorization or archive in the positive flow."""

import hashlib
import zipfile
from dataclasses import replace
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from conftest import login
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dicom_validation import InvalidDicom, read_upload, validate
from app.imaging_storage import job_path
from app.models import Assignment, AuditEvent, DicomImportJob, Study
from app.synthetic_dicom import fixture
from app.worker import process_job


@pytest.fixture
def imaging(env, tmp_path):
    env["app"].state.settings = replace(env["app"].state.settings, imaging_root=str(tmp_path))
    login(env, "staff")
    c = env["client"]
    patient = c.post(
        "/api/staff/patients", json={"local_identifier": "SYN-IMPORT-001", "display_name": "SYNTHETIC IMPORT"}
    ).json()["id"]
    sid = c.post(
        "/api/staff/studies", json={"patient_id": patient, "title": "SYNTHETIC CT", "modality": "CBCT"}
    ).json()["id"]
    aid = c.post(
        f"/api/staff/studies/{sid}/assignments",
        json={"doctor_id": env["ids"]["doctor"], "clinic_id": env["ids"]["clinic"]},
    ).json()["id"]
    uid = "2.25." + str(uuid4().int)
    data = [fixture(n, "SYN-IMPORT-001", uid) for n in range(1, 9)]
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for n, item in enumerate(data):
            archive.writestr(f"slice-{n}.dcm", item)
    env.update(sid=sid, aid=aid, uid=uid, data=data, archive=output.getvalue())
    return env


def queue(env):
    response = env["client"].post(
        f"/api/staff/studies/{env['sid']}/imports",
        content=env["archive"],
        headers={"Content-Type": "application/zip"},
    )
    assert response.status_code == 202, response.text
    job = response.json()["id"]
    process_job(env["engine"], env["app"].state.settings, UUID(job))
    return job


def publish(env, job):
    response = env["client"].post(
        f"/api/staff/studies/{env['sid']}/imports/{job}/publish", json={"confirmed": True}
    )
    assert response.status_code == 200, response.text


def test_import_review_real_dicomweb_download_and_revocation(imaging):
    e = imaging
    c = e["client"]
    sid = e["sid"]
    job = queue(e)
    jobs = c.get(f"/api/staff/studies/{sid}/imports").json()
    assert jobs[0]["state"] == "REVIEW", jobs
    assert jobs[0]["instances"] == 8
    assert (
        c.post(f"/api/staff/studies/{sid}/imports/{uuid4()}/publish", json={"confirmed": True}).status_code
        == 404
    )
    assert (
        c.post(f"/api/staff/studies/{uuid4()}/imports/{job}/publish", json={"confirmed": True}).status_code
        == 404
    )
    assert (
        c.post(f"/api/staff/studies/{sid}/imports/{job}/publish", json={"confirmed": False}).status_code
        == 409
    )
    staff_cookies = dict(c.cookies)
    staff_csrf = c.headers["X-CSRF-Token"]
    c.cookies.clear()
    login(e)
    assert c.get(f"/api/doctor/studies/{sid}/imaging").status_code == 404
    # Publishing is a distinct CSRF-protected staff action, not import completion.
    c.cookies.clear()
    c.cookies.update(staff_cookies)
    c.headers["X-CSRF-Token"] = staff_csrf
    publish(e, job)
    e["clock"][0] += __import__("datetime").timedelta(seconds=31)
    c.cookies.clear()
    login(e)
    doc_cookies = dict(c.cookies)
    doc_csrf = c.headers["X-CSRF-Token"]
    images = c.get(f"/api/doctor/studies/{sid}/imaging").json()
    single = images["instances"][0]["url"]
    assert hashlib.sha256(c.get(single).content).hexdigest() == images["instances"][0]["sha256"]
    download = c.get(images["zip_url"])
    assert download.status_code == 200
    with zipfile.ZipFile(BytesIO(download.content)) as archive:
        assert sorted(hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist()) == sorted(
            hashlib.sha256(d).hexdigest() for d in e["data"]
        )
    assert c.head(single).headers["content-length"] == str(len(e["data"][0]))
    assert c.get(single, headers={"Range": "bytes=0-131"}).content == e["data"][0][:132]
    assert c.get(single, headers={"Range": "bytes=-16"}).content == e["data"][0][-16:]
    invalid = c.get(single, headers={"Range": "bytes=999999999-"})
    assert invalid.status_code == 416 and invalid.headers["content-range"].startswith("bytes */")
    assert c.get(single, headers={"Range": "bytes=0-1,4-5"}).status_code == 416
    assert c.get(single, headers={"Range": "bytes=0-1", "If-Range": '"changed"'}).status_code == 200
    base = "/api/imaging/dicom-web"
    root = base + "/studies/" + e["uid"]
    assert c.get(base + "/studies").status_code == 404
    assert c.get(base + "/studies", params={"StudyInstanceUID": e["uid"]}).status_code == 200
    series = c.get(root + "/series")
    assert series.status_code == 200, series.text
    metadata = c.get(root + "/metadata")
    assert metadata.status_code == 200, metadata.text
    assert len(metadata.json()) == 8 and "BulkDataURI" not in metadata.text
    frame = root + "/series/" + e["uid"] + ".1/instances/" + e["uid"] + ".1.1/frames/1"
    response = c.get(
        frame, headers={"Accept": 'multipart/related; type="application/octet-stream"; transfer-syntax=*'}
    )
    assert response.status_code == 200 and len(response.content) > 30000, response.text[:100]
    for path in (
        frame.replace("/frames/1", "/frames/2"),
        frame.replace(".1.1/frames", ".1.999/frames"),
        root + "/bulk/7fe00010",
        root + "/../../system",
    ):
        assert c.get(path).status_code == 404
    assert c.get(base + "/studies", params={"00100020": "SYN-IMPORT-001"}).status_code == 400
    assert c.get(frame, headers={"Range": "bytes=0-20"}).status_code == 400
    c.cookies.clear()
    login(e, "other")
    assert c.get(single).status_code == 404
    assert c.get(frame).status_code == 404
    assert c.get(f"/api/staff/studies/{sid}/imports").status_code == 403
    c.cookies.clear()
    login(e, "admin")
    assert c.get(single).status_code == 403
    assert c.get(frame).status_code == 403
    c.cookies.clear()
    c.cookies.update(staff_cookies)
    c.headers["X-CSRF-Token"] = staff_csrf
    assert c.post(f"/api/staff/assignments/{e['aid']}/revoke").status_code == 204
    c.cookies.clear()
    c.cookies.update(doc_cookies)
    c.headers["X-CSRF-Token"] = doc_csrf
    for url in (single, images["zip_url"], frame, root + "/metadata", f"/api/doctor/studies/{sid}/imaging"):
        assert c.get(url, headers={"Range": "bytes=0-20"} if "/original" in url else {}).status_code == 404
    with Session(e["engine"]) as db:
        actions = list(db.scalars(select(AuditEvent.action)))
        assert {
            "import.queued",
            "import.validated",
            "import.published",
            "download.started",
            "download.finished",
            "dicom.read",
        } <= set(actions)


def test_invalid_import_never_publishes_and_new_job_retry(imaging):
    e = imaging
    c = e["client"]
    e["archive"] = b"not an archive"
    job = queue(e)
    assert c.get(f"/api/staff/studies/{e['sid']}/imports").json()[0]["state"] == "FAILED"
    assert (
        c.post(f"/api/staff/studies/{e['sid']}/imports/{job}/publish", json={"confirmed": True}).status_code
        == 409
    )
    e["clock"][0] += __import__("datetime").timedelta(seconds=1)
    e["archive"] = fixture(patient_id="SYN-OTHER")
    response = c.post(
        f"/api/staff/studies/{e['sid']}/imports",
        content=e["archive"],
        headers={"Content-Type": "application/dicom"},
    )
    assert response.status_code == 202
    process_job(e["engine"], e["app"].state.settings, UUID(response.json()["id"]))
    jobs = c.get(f"/api/staff/studies/{e['sid']}/imports").json()
    assert jobs[0]["error_code"] == "PATIENT_MISMATCH"
    with Session(e["engine"]) as db:
        assert db.get(Study, UUID(e["sid"])).state == "REGISTERED"


def test_archive_original_tamper_fails_closed(imaging):
    e = imaging
    job = queue(e)
    publish(e, job)
    login(e)
    images = e["client"].get(f"/api/doctor/studies/{e['sid']}/imaging").json()
    path = job_path(e["app"].state.settings, UUID(job)) / "originals.bin"
    data = path.read_bytes()
    path.write_bytes(bytes([data[0] ^ 1]) + data[1:])
    assert e["client"].get(images["zip_url"]).status_code == 503


def test_hostile_archives_and_dicom_validation(tmp_path):
    source = tmp_path / "upload.bin"
    for name in ("../outside.dcm", "/absolute.dcm", "dir/../../escape.dcm", "C:\\escape.dcm"):
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr(name, fixture())
        with pytest.raises(InvalidDicom, match="UNSAFE_ARCHIVE"):
            read_upload(source, "zip", "SYN-DEMO-001")
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bomb.dcm", b"0" * 1024 * 1024)
    with pytest.raises(InvalidDicom, match="UNSAFE_ARCHIVE"):
        read_upload(source, "zip", "SYN-DEMO-001")
    info = zipfile.ZipInfo("symlink.dcm")
    info.external_attr = 0o120777 << 16
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(info, b"../../outside")
    with pytest.raises(InvalidDicom, match="UNSAFE_ARCHIVE"):
        read_upload(source, "zip", "SYN-DEMO-001")
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("a.dcm", fixture())
        archive.writestr("b.dcm", fixture(study_uid="2.25.999"))
    with pytest.raises(InvalidDicom, match="MIXED_STUDIES"):
        read_upload(source, "zip", "SYN-DEMO-001")
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("a.dcm", fixture())
        archive.writestr("b.dcm", fixture())
    with pytest.raises(InvalidDicom, match="DUPLICATE_INSTANCE"):
        read_upload(source, "zip", "SYN-DEMO-001")
    with pytest.raises(InvalidDicom):
        validate(fixture()[:-10], "SYN-DEMO-001")
    assert not (tmp_path.parent / "outside.dcm").exists()


def test_range_rejects_excessive_numbers_as_http_error():
    from fastapi import HTTPException

    from app.imaging import byte_range

    # A long client header must produce 416 rather than Python's integer-limit ValueError/500.
    with pytest.raises(HTTPException) as error:
        byte_range("bytes=" + "9" * 5000 + "-", 100)
    assert error.value.status_code == 416


def test_download_stops_between_chunks_after_assignment_revoke(imaging):
    import asyncio

    from fastapi import Request

    from app.common import Context
    from app.imaging import file_response
    from app.models import AuthSession, User
    from app.security import digest

    e = imaging
    job = queue(e)
    publish(e, job)
    login(e)
    token = e["client"].cookies.get("fd_session")
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "headers": [],
            "app": e["app"],
            "state": {"request_id": str(uuid4())},
        }
    )
    with Session(e["engine"]) as db:
        session = db.get(AuthSession, digest(token, e["app"].state.settings, "session"))
        user = db.get(User, session.user_id)
        record = db.get(DicomImportJob, UUID(job))
        response = file_response(
            job_path(e["app"].state.settings, UUID(job)) / "originals.bin",
            record.zip_sha256,
            record.zip_size,
            "study-dicom.zip",
            request,
            Context(user, session, token),
            UUID(e["sid"]),
            db,
        )
        db.commit()

    # The producer must continue using captured IDs after its ORM session has closed.
    async def consume():
        stream = response.body_iterator
        first = await anext(stream)
        assert len(first) == 64 * 1024
        with Session(e["engine"]) as db, db.begin():
            assignment = db.get(Assignment, UUID(e["aid"]))
            assignment.revoked_at = e["clock"][0]
        with pytest.raises(StopAsyncIteration):
            await anext(stream)

    asyncio.run(consume())
    with Session(e["engine"]) as db:
        assert (
            db.scalar(select(AuditEvent.result).where(AuditEvent.action == "download.finished")) == "aborted"
        )


def test_worker_retry_after_interrupted_write_keeps_private_state(imaging, monkeypatch):
    import app.worker as worker

    e = imaging
    response = e["client"].post(
        f"/api/staff/studies/{e['sid']}/imports",
        content=e["archive"],
        headers={"Content-Type": "application/zip"},
    )
    job_id = UUID(response.json()["id"])
    real_write = worker.write_private

    def interrupted(path, data):
        real_write(path, data)
        raise SystemExit("synthetic interrupted worker")

    with monkeypatch.context() as patch:
        patch.setattr(worker, "write_private", interrupted)
        with pytest.raises(SystemExit):
            process_job(e["engine"], e["app"].state.settings, job_id)
    with Session(e["engine"]) as db:
        assert db.get(DicomImportJob, job_id).state == "QUEUED"
        assert db.get(Study, UUID(e["sid"])).state == "REGISTERED"
    process_job(e["engine"], e["app"].state.settings, job_id)
    with Session(e["engine"]) as db:
        assert db.get(DicomImportJob, job_id).state == "REVIEW"
        assert db.get(Study, UUID(e["sid"])).state == "REGISTERED"


def test_openapi_operation_ids_are_unique():
    from cryptography.fernet import Fernet

    from app.config import Settings
    from app.main import create_app

    app = create_app(
        Settings(
            database_url="postgresql+psycopg://unused@127.0.0.1/unused",
            auth_key="synthetic-key-for-validation-only-12345",
            totp_key=Fernet.generate_key().decode(),
            public_origin="http://127.0.0.1:5173",
            development=True,
        )
    )
    schema = app.openapi()
    app.state.engine.dispose()
    ids = [operation["operationId"] for path in schema["paths"].values() for operation in path.values()]
    assert len(ids) == len(set(ids)), "GET and HEAD must not share an OpenAPI operation ID"


def test_imaging_config_rejects_remote_database_without_connecting():
    from cryptography.fernet import Fernet

    from app.config import Settings

    with pytest.raises(ValueError, match="local synthetic database"):
        Settings(
            database_url="postgresql+psycopg://test@clinical.invalid/familydent_dev",
            auth_key="synthetic-key-for-validation-only-12345",
            totp_key=Fernet.generate_key().decode(),
            public_origin="http://127.0.0.1:5173",
            development=True,
            imaging_root="/tmp/synthetic",
        )
