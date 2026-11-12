"""Auth dependencies: staff/worker identity, role + facility scoping, CSRF, patient device key."""

import hmac
import uuid
from collections.abc import Callable, Iterable

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import AppError, forbidden
from app.core.security import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER, decode_token, sha256_hex
from app.models import Facility, Patient, User
from app.models.enums import HOSPITAL_ROLES, Role, VerificationStatus

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def check_csrf(request: Request) -> None:
    """Double-submit: the X-CSRF-Token header must equal the vt_csrf cookie on mutations."""
    if request.method in SAFE_METHODS:
        return
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get(CSRF_HEADER)
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise AppError(403, "csrf_failed", "Missing or invalid CSRF token")


async def current_user_any_status(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    payload = decode_token(token, "access") if token else None
    if not payload:
        raise AppError(401, "unauthorized", "Please sign in")
    user = await db.get(User, uuid.UUID(payload["sub"]))
    if not user:
        raise AppError(401, "unauthorized", "Please sign in")
    check_csrf(request)
    return user


async def current_user(user: User = Depends(current_user_any_status)) -> User:
    """Only approved users (at an approved facility, for hospital roles) reach work screens."""
    if user.status != VerificationStatus.approved:
        raise AppError(403, "not_verified", f"Account is {user.status}", {"status": user.status})
    return user


def require_roles(*roles: Role) -> Callable:
    allowed = set(roles)

    async def dep(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise forbidden("Your role cannot do this")
        return user

    return dep


def require_hospital_staff(*roles: Role) -> Callable:
    """Hospital roles scoped to their facility. Returns the user; use user.facility_id for scoping."""
    allowed: Iterable[Role] = roles or tuple(HOSPITAL_ROLES)

    async def dep(
        user: User = Depends(require_roles(*allowed)), db: AsyncSession = Depends(get_db)
    ) -> User:
        if user.facility_id is None:
            raise forbidden("No facility attached to this account")
        facility = await db.get(Facility, user.facility_id)
        if not facility or facility.status != VerificationStatus.approved:
            raise AppError(403, "facility_not_verified", "Your facility is not verified yet")
        return user

    return dep


def ensure_same_facility(user: User, facility_id: uuid.UUID | None) -> None:
    if facility_id is None or user.facility_id != facility_id:
        # 404 rather than 403 so other facilities' IDs are not confirmed to exist.
        raise AppError(404, "not_found", "Not found")


async def current_patient(request: Request, db: AsyncSession = Depends(get_db)) -> Patient:
    key = request.headers.get("x-patient-key")
    if not key or len(key) > 128:
        raise AppError(401, "patient_key_required", "Device key missing")
    patient = (
        await db.execute(select(Patient).where(Patient.device_key_hash == sha256_hex(key)))
    ).scalar_one_or_none()
    if not patient:
        raise AppError(401, "patient_key_invalid", "Device key not recognised")
    return patient
