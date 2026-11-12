"""Private local paths: only server-generated UUID components, never upload names."""

import hashlib
import os
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException

from .config import Settings


def storage(settings: Settings) -> Path:
    if not settings.imaging_root:
        raise HTTPException(503, "IMAGING_DISABLED")
    root = Path(settings.imaging_root)
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    return root


def job_path(settings: Settings, job_id: UUID) -> Path:
    return storage(settings) / str(job_id)


def write_private(path: Path, data: bytes):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as target:
        target.write(data)


def checksum(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()
