"""Demo patients: open a seeded demo patient's record on a phone in one tap (synthetic data only, audited).

Staff always sign in with email and password. DEMO_LOGINS=false turns this off.
"""

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError, Envelope, ok
from app.core.ratelimit import limiter
from app.core.security import new_secret, sha256_hex
from app.models import Patient

router = APIRouter(prefix="/demo", tags=["demo"])


class DemoPatient(BaseModel):
    vitalis_id: str
    name: str


class DemoAccounts(BaseModel):
    patients: list[DemoPatient]


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
    patients = [
        DemoPatient(vitalis_id=p.vitalis_id, name=p.display_name or p.vitalis_id)
        for p in (await db.execute(_demo_patients().order_by(Patient.display_name))).scalars()
    ]
    return ok(DemoAccounts(patients=patients))


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
