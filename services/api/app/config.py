import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from sqlalchemy.engine import make_url


@dataclass(frozen=True)
class Settings:
    database_url: str = field(repr=False)
    totp_key: str = field(repr=False)
    auth_key: str = field(repr=False)
    public_origin: str
    development: bool = False
    imaging_root: str = ""
    orthanc_url: str = "http://127.0.0.1:8044"
    viewer_origin: str = "http://127.0.0.1:8091"

    def __post_init__(self):
        if self.imaging_root:
            # This first integration is explicitly local and synthetic-only.
            if not self.development:
                raise ValueError("Imaging is currently restricted to local development")
            database = make_url(self.database_url)
            if database.host not in {"127.0.0.1", "localhost"} or database.database not in {
                "familydent_dev",
                "familydent_test",
            }:
                raise ValueError("Imaging requires a local synthetic database")
            archive = urlsplit(self.orthanc_url)
            if archive.scheme != "http" or archive.hostname not in {"127.0.0.1", "localhost"} or archive.path:
                raise ValueError("Only the isolated loopback Orthanc is allowed")
            viewer = urlsplit(self.viewer_origin)
            if viewer.scheme != "http" or viewer.hostname != "127.0.0.1" or viewer.path:
                raise ValueError("Only the local synthetic viewer is allowed")
        Fernet(self.totp_key.encode())
        if len(self.auth_key) < 32:
            raise ValueError("AUTH_KEY must contain at least 32 characters")
        origin = urlsplit(self.public_origin)
        if origin.path or origin.query or origin.fragment or not origin.netloc:
            raise ValueError("PUBLIC_ORIGIN must be an origin, without path")
        if not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("PostgreSQL with psycopg is required")
        if not self.development and origin.scheme != "https":
            raise ValueError("HTTPS is required outside development")
        if self.development and origin.hostname not in {"localhost", "127.0.0.1", "testserver"}:
            raise ValueError("Development requires a loopback origin")

    @classmethod
    def from_env(cls):
        return cls(
            database_url=os.environ["DATABASE_URL"],
            totp_key=os.environ["TOTP_KEY"],
            auth_key=os.environ["AUTH_KEY"],
            public_origin=os.environ["PUBLIC_ORIGIN"],
            development=os.getenv("DEVELOPMENT") == "true",
            imaging_root=os.getenv("IMAGING_ROOT", ""),
            orthanc_url=os.getenv("ORTHANC_URL", "http://127.0.0.1:8044"),
            viewer_origin=os.getenv("VIEWER_ORIGIN", "http://127.0.0.1:8091"),
        )
