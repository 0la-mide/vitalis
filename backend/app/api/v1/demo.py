"""One-tap demo sign-in for judging: seeded @vitalis.demo staff and the seeded demo patients only.

Off in production unless DEMO_LOGINS=true. Synthetic data only; every use is audited.
"""

import uuid

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import _me, _set_session_cookies
from app.core.audit import audit
from app.core.config import get_settings
from app.core.db import get_db, utcnow
from app.core.errors import AppError, Envelope, ok
from app.core.ratelimit import limiter
from app.core.security import new_secret, sha256_hex
from app.models import Facility, Patient, User
from app.schemas.auth import MeOut

router = APIRouter(prefix="/demo", tags=["demo"])
DEMO_DOMAIN = "@vitalis.demo"


class DemoStaff(BaseModel):
    email: str
    name: str
    role: str
    status: str
    facility: str | None


class DemoPatient(BaseModel):
    vitalis_id: str
    name: str


class DemoAccounts(BaseModel):
    staff: list[DemoStaff]
    patients: list[DemoPatient]


class DemoLoginIn(BaseModel):
    email: str


class DemoPatientIn(BaseModel):
    vitalis_id: str


class DemoPatientOut(BaseModel):
    patient_id: uuid.UUID
    vitalis_id: str
    device_key: str


def _require_enabled() -> None:
    if not get_settings().demo_logins_enabled:
        raise AppError(404, "not_found", "Not found")


def _demo_patients():
    return select(Patient).where(Patient.display_name.is_not(None), Patient.display_name.like("%(demo)"))


@router.get("/accounts", response_model=Envelope[DemoAccounts])
async def accounts(db: AsyncSession = Depends(get_db)):
    _require_enabled()
    rows = (
        await db.execute(
            select(User, Facility.name)
            .outerjoin(Facility, Facility.id == User.facility_id)
            .where(func.lower(User.email).like(f"%{DEMO_DOMAIN}"))
            .order_by(Facility.name.nulls_first(), User.email)
        )
    ).all()
    staff = [
        DemoStaff(email=u.email, name=u.full_name, role=u.role, status=u.status, facility=fname)
        for u, fname in rows
    ]
    patients = [
        DemoPatient(vitalis_id=p.vitalis_id, name=p.display_name or p.vitalis_id)
        for p in (await db.execute(_demo_patients().order_by(Patient.display_name))).scalars()
    ]
    return ok(DemoAccounts(staff=staff, patients=patients))


@router.post("/login", response_model=Envelope[MeOut])
@limiter.limit("30/minute")
async def demo_login(request: Request, body: DemoLoginIn, response: Response, db: AsyncSession = Depends(get_db)):
    _require_enabled()
    email = body.email.strip().lower()
    user = None
    if email.endswith(DEMO_DOMAIN):
        user = (await db.execute(select(User).where(func.lower(User.email) == email))).scalar_one_or_none()
    if not user:
        raise AppError(404, "not_found", "No demo account with that email")
    user.last_login_at = utcnow()
    await audit(db, "auth.demo_login", actor_id=user.id, facility_id=user.facility_id)
    await db.commit()
    csrf = _set_session_cookies(response, user)
    return ok(await _me(db, user, csrf))


@router.post("/patient", response_model=Envelope[DemoPatientOut])
@limiter.limit("30/minute")
async def demo_patient(request: Request, body: DemoPatientIn, db: AsyncSession = Depends(get_db)):
    """Opens a demo patient's record on this phone. Rotates the device key only (the recovery code stays)."""
    _require_enabled()
    p = (
        await db.execute(_demo_patients().where(Patient.vitalis_id == body.vitalis_id.strip().upper()))
    ).scalar_one_or_none()
    if not p:
        raise AppError(404, "not_found", "No demo patient with that VITALIS ID")
    key = new_secret(32)
    p.device_key_hash = sha256_hex(key)
    await audit(db, "patient.demo_open", actor_type="patient", actor_id=p.id, subject_type="patient", subject_id=p.id)
    await db.commit()
    return ok(DemoPatientOut(patient_id=p.id, vitalis_id=p.vitalis_id, device_key=key))
