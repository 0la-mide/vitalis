from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.db import get_db
from app.core.errors import AppError, Envelope, ok
from app.core.ratelimit import limiter
from app.core.security import secret_matches
from app.models import Patient
from app.schemas.triage import PatientKeysOut, PatientRecoverIn, PatientStartIn
from app.services.patients import create_patient, normalise_recovery, rotate_keys

router = APIRouter(prefix="/patients", tags=["patient"])


@router.post("/start", response_model=Envelope[PatientKeysOut])
@limiter.limit("10/minute")
async def start(request: Request, body: PatientStartIn, db: AsyncSession = Depends(get_db)):
    """No login. Creates a patient and returns a device key + one-time recovery code (shown once)."""
    p, key, recovery = await create_patient(db, phone=body.phone)
    await audit(db, "patient.start", actor_type="patient", actor_id=p.id, subject_type="patient", subject_id=p.id)
    await db.commit()
    return ok(PatientKeysOut(patient_id=p.id, vitalis_id=p.vitalis_id, device_key=key, recovery_code=recovery))


@router.post("/recover", response_model=Envelope[PatientKeysOut])
@limiter.limit("5/minute")
async def recover(request: Request, body: PatientRecoverIn, db: AsyncSession = Depends(get_db)):
    p = (
        await db.execute(select(Patient).where(Patient.vitalis_id == body.vitalis_id.strip().upper()))
    ).scalar_one_or_none()
    expected = p.recovery_hash if p else "0" * 64
    if not secret_matches(normalise_recovery(body.recovery_code), expected) or not p:
        raise AppError(401, "recovery_failed", "VITALIS ID or recovery code is wrong")
    key, recovery = rotate_keys(p)
    await audit(db, "patient.recover", actor_type="patient", actor_id=p.id, subject_type="patient", subject_id=p.id)
    await db.commit()
    return ok(PatientKeysOut(patient_id=p.id, vitalis_id=p.vitalis_id, device_key=key, recovery_code=recovery))
