"""Explicit local entrypoint; does not run migrations implicitly."""

import os
from pathlib import Path

import uvicorn


def load_local_env():
    path = Path(__file__).resolve().parents[3] / "infra/local/.env"
    for line in path.read_text().splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)
    return path


def local_settings():
    load_local_env()
    os.environ.setdefault("DATABASE_URL", os.environ["DEV_DATABASE_URL"])
    os.environ.setdefault("PUBLIC_ORIGIN", "http://127.0.0.1:5173")
    os.environ["DEVELOPMENT"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ.setdefault(
        "IMAGING_ROOT", str(Path(__file__).resolve().parents[3] / "infra/local/imaging-data")
    )


if __name__ == "__main__":
    local_settings()
    uvicorn.run("app.main:app_factory", factory=True, host="127.0.0.1", port=8100, access_log=False)
