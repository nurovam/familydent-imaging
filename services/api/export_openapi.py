"""Reproducible contract export, no database connection or real secrets."""

import json
import sys
from pathlib import Path

from cryptography.fernet import Fernet

from app.config import Settings
from app.main import create_app

settings = Settings(
    database_url="postgresql+psycopg://unused@127.0.0.1/unused",
    totp_key=Fernet.generate_key().decode(),
    auth_key="synthetic-contract-export-key-00000000",
    public_origin="http://127.0.0.1:5173",
    development=True,
)
app = create_app(settings)
body = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
path = Path(__file__).resolve().parents[2] / "packages/contracts/openapi.json"
if "--check" in sys.argv:
    if not path.exists() or path.read_text() != body:
        raise SystemExit("OpenAPI snapshot is outdated. Run export_openapi.py.")
else:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
print("OpenAPI contract verified" if "--check" in sys.argv else "OpenAPI contract exported")
app.state.engine.dispose()
