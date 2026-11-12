import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from cryptography.fernet import Fernet


@dataclass(frozen=True)
class Settings:
    database_url: str = field(repr=False)
    totp_key: str = field(repr=False)
    auth_key: str = field(repr=False)
    public_origin: str
    development: bool = False

    def __post_init__(self):
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
        )
