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


if __name__ == "__main__":
    load_local_env()
    os.environ["DATABASE_URL"] = os.environ["DEV_DATABASE_URL"]
    os.environ["PUBLIC_ORIGIN"] = "http://127.0.0.1:5173"
    os.environ["DEVELOPMENT"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    uvicorn.run("app.main:app_factory", factory=True, host="127.0.0.1", port=8100, access_log=False)
