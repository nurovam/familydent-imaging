import secrets
from datetime import timedelta

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from .common import Context, audit, authenticated, database, deny, lock_account, mutation, throttle
from .models import AuthChallenge, AuthSession, User
from .schemas import AccountResponse
from .security import decrypt_secret, digest, encrypt_secret, verify_password

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class PasswordInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)


class CodeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern=r"^[0-9]{6}$")


def set_cookie(response: Response, request: Request, key: str, token: str, seconds: int):
    response.set_cookie(
        key,
        token,
        max_age=seconds,
        httponly=True,
        samesite="strict",
        secure=not request.app.state.settings.development,
    )


def get_challenge(request: Request, db: Session) -> AuthChallenge:
    hashed = digest(request.cookies.get("fd_challenge", ""), request.app.state.settings, "challenge")
    challenge = db.get(AuthChallenge, hashed)
    if challenge:
        # Shared lock order with account disabling: user first, then challenge/session.
        lock_account(db, challenge.user_id)
        challenge = db.get(AuthChallenge, hashed, with_for_update=True, populate_existing=True)
    if (
        not challenge
        or challenge.consumed_at
        or challenge.attempts >= 5
        or challenge.expires_at <= request.app.state.now()
    ):
        deny(db, request, "CHALLENGE_INVALID")
    return challenge


@router.post("/password")
def password_login(
    data: PasswordInput,
    request: Request,
    response: Response,
    db: Session = Depends(database, scope="function"),
):
    settings = request.app.state.settings
    email = data.email.strip().lower()
    account_limit = throttle(db, request, "password-account", email, 5)
    throttle(db, request, "password-ip", request.client.host if request.client else "unknown", 30)
    user = db.scalar(select(User).where(User.email == email))
    valid = verify_password(data.password.get_secret_value(), user.password_hash if user else None)
    if not valid or not user or not user.active:
        deny(db, request)
    # A new challenge supersedes only this browser's old challenge, not another user's login.
    previous = db.get(AuthChallenge, digest(request.cookies.get("fd_challenge", ""), settings, "challenge"))
    if previous:
        previous.consumed_at = request.app.state.now()
    token = secrets.token_urlsafe(32)
    pending = encrypt_secret(pyotp.random_base32(), settings) if not user.totp_secret else None
    db.add(
        AuthChallenge(
            token_hash=digest(token, settings, "challenge"),
            user_id=user.id,
            expires_at=request.app.state.now() + timedelta(minutes=5),
            pending_secret=pending,
        )
    )
    account_limit.attempts = 0
    audit(db, request, "auth.password_verified", actor=user.id)
    db.commit()
    set_cookie(response, request, "fd_challenge", token, 300)
    return {"next": "enroll_totp" if pending else "verify_totp"}


@router.post("/totp/enroll")
def enrollment(request: Request, db: Session = Depends(database, scope="function")):
    challenge = get_challenge(request, db)
    user = db.get(User, challenge.user_id)
    if not user or not user.active:
        deny(db, request)
    if user.totp_secret or not challenge.pending_secret:
        raise HTTPException(409, "ALREADY_ENROLLED")
    secret = decrypt_secret(challenge.pending_secret, request.app.state.settings)
    audit(db, request, "auth.enrollment_viewed", actor=user.id)
    return {
        "secret": secret,
        "provisioning_uri": pyotp.TOTP(secret).provisioning_uri(
            name=user.email, issuer_name="FamilyDent Imaging"
        ),
    }


@router.post("/totp")
def verify_totp(
    data: CodeInput, request: Request, response: Response, db: Session = Depends(database, scope="function")
):
    challenge = get_challenge(request, db)
    user = lock_account(db, challenge.user_id)
    if not user or not user.active:
        deny(db, request)
    account_limit = throttle(db, request, "totp-account", str(user.id), 5)
    encrypted = user.totp_secret or challenge.pending_secret
    if not encrypted:
        deny(db, request)
    now = request.app.state.now()
    totp = pyotp.TOTP(decrypt_secret(encrypted, request.app.state.settings))
    counter = totp.timecode(now)
    matches = [
        counter + offset
        for offset in (-1, 0, 1)
        if pyotp.utils.strings_equal(totp.at(now, offset), data.code)
    ]
    code = max(matches, default=-1)
    if code <= user.last_totp_counter:
        challenge.attempts += 1
        deny(db, request, actor=user.id, action="auth.totp_failed")
    account_limit.attempts = 0
    user.last_totp_counter = code
    user.totp_secret = encrypted
    challenge.consumed_at = now
    challenge.pending_secret = None
    old = db.get(
        AuthSession, digest(request.cookies.get("fd_session", ""), request.app.state.settings, "session")
    )
    if old:
        old.revoked_at = now
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token_hash=digest(token, request.app.state.settings, "session"),
            user_id=user.id,
            created_at=now,
            last_seen_at=now,
        )
    )
    audit(db, request, "auth.mfa_success", actor=user.id)
    db.commit()
    response.delete_cookie(
        "fd_challenge", secure=not request.app.state.settings.development, httponly=True, samesite="strict"
    )
    set_cookie(response, request, "fd_session", token, 8 * 3600)
    return {"authenticated": True}


@router.get("/me", response_model=AccountResponse)
def me(request: Request, ctx: Context = Depends(authenticated)):
    return {
        "id": str(ctx.user.id),
        "display_name": ctx.user.display_name,
        "role": ctx.user.role,
        "csrf_token": digest(ctx.token, request.app.state.settings, "csrf"),
    }


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    ctx: Context = Depends(mutation),
    db: Session = Depends(database, scope="function"),
):
    ctx.session.revoked_at = request.app.state.now()
    audit(db, request, "auth.logout", actor=ctx.user.id)
    response.delete_cookie(
        "fd_session", secure=not request.app.state.settings.development, httponly=True, samesite="strict"
    )
