import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.config import get_settings
from app.core.db import get_db, utcnow
from app.core.deps import check_csrf, current_user_any_status
from app.core.errors import AppError, Envelope, ok
from app.core.ratelimit import limiter
from app.core.security import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    REFRESH_COOKIE,
    create_token,
    decode_token,
    new_secret,
    verify_password,
)
from app.models import Facility, User
from app.schemas.auth import FacilityBrief, LoginIn, MeOut

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_PATH = "/api/v1/auth"


def _set_session_cookies(response: Response, user: User) -> str:
    s = get_settings()
    csrf = new_secret(24)
    common = {"secure": s.cookie_secure, "samesite": "lax"}
    response.set_cookie(
        ACCESS_COOKIE,
        create_token(user.id, "access", {"role": user.role}),
        httponly=True,
        max_age=s.access_token_minutes * 60,
        path="/",
        **common,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        create_token(user.id, "refresh"),
        httponly=True,
        max_age=s.refresh_token_days * 86400,
        path=REFRESH_PATH,
        **common,
    )
    # Readable by JS so the client can echo it in X-CSRF-Token.
    response.set_cookie(
        CSRF_COOKIE, csrf, httponly=False, max_age=s.refresh_token_days * 86400, path="/", **common
    )
    return csrf


async def _me(db: AsyncSession, user: User, csrf: str | None = None) -> MeOut:
    facility = await db.get(Facility, user.facility_id) if user.facility_id else None
    return MeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        status_reason=user.status_reason,
        facility=FacilityBrief(id=facility.id, name=facility.name, status=facility.status)
        if facility
        else None,
        csrf_token=csrf,
    )


@router.post("/login", response_model=Envelope[MeOut])
@limiter.limit("10/minute")
async def login(request: Request, body: LoginIn, response: Response, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(select(User).where(func.lower(User.email) == body.email.lower()))
    ).scalar_one_or_none()
    if not verify_password(body.password, user.password_hash if user else None) or not user:
        raise AppError(401, "invalid_credentials", "Email or password is incorrect")
    user.last_login_at = utcnow()
    await audit(db, "auth.login", actor_id=user.id, facility_id=user.facility_id)
    await db.commit()
    csrf = _set_session_cookies(response, user)
    return ok(await _me(db, user, csrf))


@router.post("/refresh", response_model=Envelope[MeOut])
@limiter.limit("30/minute")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    check_csrf(request)
    token = request.cookies.get(REFRESH_COOKIE)
    payload = decode_token(token, "refresh") if token else None
    if not payload:
        raise AppError(401, "unauthorized", "Please sign in")
    user = await db.get(User, uuid.UUID(payload["sub"]))
    if not user:
        raise AppError(401, "unauthorized", "Please sign in")
    csrf = _set_session_cookies(response, user)
    return ok(await _me(db, user, csrf))


@router.post("/logout", response_model=Envelope[dict])
async def logout(response: Response):
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)
    response.delete_cookie(CSRF_COOKIE, path="/")
    return ok({"signed_out": True})


@router.get("/me", response_model=Envelope[MeOut])
async def me(user: User = Depends(current_user_any_status), db: AsyncSession = Depends(get_db)):
    """Available to pending/rejected/suspended users too: it powers their status page."""
    return ok(await _me(db, user))
