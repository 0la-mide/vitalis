"""Hospital side of record sharing: redeem a patient's QR, ask for access, read the shared record."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.db import get_db, utcnow
from app.core.deps import require_hospital_staff
from app.core.errors import AppError, Envelope, ok
from app.core.ratelimit import limiter
from app.core.security import sha256_hex
from app.models import AccessRequest, Consent, Encounter, Patient, QRGrant, Referral, User
from app.realtime.broker import broker
from app.services import records as rsvc

router = APIRouter(tags=["shared record"])
any_staff = require_hospital_staff()


class RedeemIn(BaseModel):
    token: str = Field(min_length=20, max_length=100)


class ConsentInfo(BaseModel):
    scope: str
    via: str
    expires_at: datetime


class RedeemOut(BaseModel):
    patient_id: uuid.UUID
    vitalis_id: str
    consent: ConsentInfo
    encounter_id: uuid.UUID | None  # open visit at this hospital, if any


class ConsentStatus(BaseModel):
    active: bool
    consent: ConsentInfo | None
    pending_request: bool
    hidden_history: int
    other_hospital_visits: int


class NetworkRecord(BaseModel):
    vitalis_id: str
    consent: ConsentInfo
    history: list[dict]
    visits: list[dict]  # visits at OTHER hospitals


class AccessIn(BaseModel):
    purpose: str = Field(default="Treatment at this hospital", min_length=3, max_length=200)


def _info(c: Consent) -> ConsentInfo:
    return ConsentInfo(scope=c.scope, via=c.via, expires_at=c.expires_at)


async def _has_relationship(db: AsyncSession, patient_id: uuid.UUID, facility_id: uuid.UUID) -> bool:
    """Staff may only ask about patients who came to their hospital (a visit or a referral)."""
    enc = (await db.execute(select(Encounter.id).where(Encounter.patient_id == patient_id,
                                                       Encounter.facility_id == facility_id).limit(1))).first()
    ref = (await db.execute(select(Referral.id).where(Referral.patient_id == patient_id,
                                                      Referral.facility_id == facility_id).limit(1))).first()
    return bool(enc or ref)


@router.post("/qr/redeem", response_model=Envelope[RedeemOut])
@limiter.limit("30/minute")
async def redeem(request: Request, body: RedeemIn, user: User = Depends(any_staff), db: AsyncSession = Depends(get_db)):
    g = (await db.execute(select(QRGrant).where(QRGrant.token_hash == sha256_hex(body.token)))).scalar_one_or_none()
    if not g:
        raise AppError(404, "qr_invalid", "This QR code is not valid")
    consent = await db.get(Consent, g.consent_id)
    now = utcnow()
    if g.revoked_at or (consent and consent.revoked_at):
        raise AppError(410, "qr_revoked", "The patient cancelled this QR code")
    if g.redeemed_at:
        raise AppError(410, "qr_used", "This QR code was already used. Ask the patient for a new one.")
    if g.expires_at <= now:
        raise AppError(410, "qr_expired", "This QR code has expired. Ask the patient for a new one.")
    if consent.facility_id and consent.facility_id != user.facility_id:
        raise AppError(403, "qr_other_facility", "This QR code was made for a different hospital")
    g.redeemed_at, g.redeemed_by = now, user.id
    consent.activated_at, consent.activated_facility_id = now, user.facility_id
    consent.expires_at = now + timedelta(hours=rsvc.CONSENT_HOURS)
    patient = await db.get(Patient, consent.patient_id)
    enc = (await db.execute(select(Encounter.id).where(
        Encounter.patient_id == patient.id, Encounter.facility_id == user.facility_id,
        Encounter.state.not_in(["completed", "cancelled"])).order_by(Encounter.created_at.desc()).limit(1))).scalar()
    await audit(db, "qr.redeem", actor_id=user.id, subject_type="patient", subject_id=patient.id,
                facility_id=user.facility_id, details={"scope": consent.scope})
    await db.commit()
    broker.publish(f"facility:{user.facility_id}", "consent.active", {"patient_id": patient.id})
    return ok(RedeemOut(patient_id=patient.id, vitalis_id=patient.vitalis_id, consent=_info(consent), encounter_id=enc))


@router.get("/hospital/patients/{patient_id}/consent", response_model=Envelope[ConsentStatus])
async def consent_status(patient_id: uuid.UUID, user: User = Depends(any_staff), db: AsyncSession = Depends(get_db)):
    if not await _has_relationship(db, patient_id, user.facility_id):
        raise AppError(404, "not_found", "Not found")
    c = await rsvc.active_consent(db, patient_id, user.facility_id)
    pending = (await db.execute(select(AccessRequest.id).where(
        AccessRequest.patient_id == patient_id, AccessRequest.facility_id == user.facility_id,
        AccessRequest.status == "pending", AccessRequest.expires_at > utcnow()))).first()
    others = (await db.execute(select(Encounter.id).where(Encounter.patient_id == patient_id,
                                                          Encounter.facility_id != user.facility_id))).all()
    return ok(ConsentStatus(active=bool(c), consent=_info(c) if c else None, pending_request=bool(pending),
                            hidden_history=0 if c else await rsvc.hidden_history_count(db, patient_id, user.facility_id),
                            other_hospital_visits=len(others)))


@router.post("/hospital/patients/{patient_id}/access-requests", response_model=Envelope[ConsentStatus])
@limiter.limit("10/minute")
async def request_access(request: Request, patient_id: uuid.UUID, body: AccessIn, user: User = Depends(any_staff),
                         db: AsyncSession = Depends(get_db)):
    if not await _has_relationship(db, patient_id, user.facility_id):
        raise AppError(404, "not_found", "Not found")
    db.add(AccessRequest(patient_id=patient_id, facility_id=user.facility_id, requested_by=user.id,
                         purpose=body.purpose.strip(), expires_at=utcnow() + timedelta(minutes=30)))
    await audit(db, "access.request", actor_id=user.id, subject_type="patient", subject_id=patient_id,
                facility_id=user.facility_id)
    await db.commit()
    return await consent_status(patient_id, user, db)


@router.get("/hospital/patients/{patient_id}/network-record", response_model=Envelope[NetworkRecord])
async def network_record(patient_id: uuid.UUID, user: User = Depends(any_staff), db: AsyncSession = Depends(get_db)):
    c = await rsvc.active_consent(db, patient_id, user.facility_id)
    if not c:
        raise AppError(403, "consent_required", "The patient has not shared their record with this hospital")
    patient = await db.get(Patient, patient_id)
    other = list((await db.execute(select(Encounter.id).where(
        Encounter.patient_id == patient_id, Encounter.facility_id != user.facility_id))).scalars())
    out = NetworkRecord(
        vitalis_id=patient.vitalis_id, consent=_info(c),
        history=await rsvc.history_rows(db, rsvc.history_filter(patient_id, user.facility_id, c)),
        visits=await rsvc.visits(db, other) if c.scope == "full" else [],
    )
    await audit(db, "record.network.view", actor_id=user.id, subject_type="patient", subject_id=patient_id,
                facility_id=user.facility_id, details={"visits": len(out.visits), "scope": c.scope})
    await db.commit()
    return ok(out)
