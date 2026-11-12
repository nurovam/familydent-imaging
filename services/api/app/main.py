from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from . import admin, auth, studies
from .config import Settings


def create_app(settings: Settings, now=None) -> FastAPI:
    app = FastAPI(
        title="FamilyDent Imaging API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.development else None,
    )
    app.state.settings = settings
    app.state.now = now or (lambda: datetime.now(UTC))
    app.state.engine = create_engine(settings.database_url, pool_pre_ping=True, hide_parameters=True)

    @app.middleware("http")
    async def boundaries(request: Request, call_next):
        request.state.request_id = str(uuid4())
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and request.headers.get("origin") != settings.public_origin
        ):
            response = JSONResponse(
                {"code": "ORIGIN_DENIED", "request_id": request.state.request_id}, status_code=403
            )
        else:
            response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        return JSONResponse(
            {"code": error.detail, "request_id": request.state.request_id}, status_code=error.status_code
        )

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, error: RequestValidationError):
        # Never return submitted passwords, OTPs or medical values in validation errors.
        return JSONResponse(
            {"code": "INVALID_INPUT", "request_id": request.state.request_id}, status_code=422
        )

    @app.exception_handler(IntegrityError)
    async def conflict(request: Request, error: IntegrityError):
        return JSONResponse({"code": "CONFLICT", "request_id": request.state.request_id}, status_code=409)

    @app.get("/api/health")
    def health():
        with app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(studies.router)
    app.include_router(admin.router)
    return app


def app_factory():
    return create_app(Settings.from_env())
