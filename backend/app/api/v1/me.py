"""The patient's own record and consent controls (X-Patient-Key). No login, no names needed."""

import base64
import io
import uuid
from datetime import datetime, timedelta
from typing import Literal

import qrcode
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.config import get_settings
from app.core.db import get_db, utcnow
from app.core.deps import current_patient
from app.core.errors import AppError, Envelope, ok
from app.core.ratelimit import limiter, patient_key
from app.core.security import new_secret, sha256_hex
from app.models import AccessRequest, AuditEvent, Consent, Facility, Patient, QRGrant, Referral, User
from app.models.enums import VerificationStatus
from app.services import records as rsvc

router = APIRouter(prefix="/me", tags=["my record"])

LOOK_ACTIONS = {"record.view": "viewed your record", "record.network.view": "viewed your records from other hospitals",
                "qr.redeem": "opened your shared record with your QR code", "encounter.view": "opened your visit",
                "ai.draft.create": "used VITALIS AI on your record", "prescription.create": "prescribed for you",
                "access.request": "asked to see your record", "record.add": "added to your record"}


class MyRecord(BaseModel):
    vitalis_id: str
    history: list[dict]
    visits: list[dict]
    triage: list[dict]
    referrals: list[dict]
    chemist_vitals: list[dict]


class ShareIn(BaseModel):
    facility_id: uuid.UUID | None = None  # None = any verified facility
    scope: Literal["full", "summary"] = "full"


class ShareOut(BaseModel):
    consent_id: uuid.UUID
    url: str
    qr_png: str  # data: URI
    expires_at: datetime
    facility_name: str | None


class ConsentRow(BaseModel):
    id: uuid.UUID
    facility_name: str | None
    scope: str
    via: str
    created_at: datetime
    expires_at: datetime
    activated_at: datetime | None
    revoked_at: datetime | None
    active: bool


class LookEvent(BaseModel):
    at: datetime
    who: str | None
    role: str | None
    facility: str | None
    what: str


class AccessLog(BaseModel):
    consents: list[ConsentRow]
    events: list[LookEvent]


class RequestRow(BaseModel):
    id: uuid.UUID
    facility_name: str
    requested_by: str
    purpose: str
    created_at: datetime
    expires_at: datetime


class DecideIn(BaseModel):
    decision: Literal["allow", "deny"]


@router.get("/records", response_model=Envelope[MyRecord])
async def my_records(patient: Patient = Depends(current_patient), db: AsyncSession = Depends(get_db)):
    t = await rsvc.patient_timeline(db, patient.id)
    return ok(MyRecord(vitalis_id=patient.vitalis_id, **t))


@router.post("/consents", response_model=Envelope[ShareOut])
@limiter.limit("20/hour", key_func=patient_key)
async def share(request: Request, body: ShareIn, patient: Patient = Depends(current_patient),
                db: AsyncSession = Depends(get_db)):
    """Creates a consent and a 10-minute, single-use QR. The QR holds only a link with a random token."""
    fac = None
    if body.facility_id:
        fac = await db.get(Facility, body.facility_id)
        if not fac or fac.status != VerificationStatus.approved:
            raise AppError(422, "facility_not_verified", "Choose a verified hospital")
    consent = rsvc.new_consent(patient.id, body.facility_id, via="qr", scope=body.scope, activate=False)
    db.add(consent)
    await db.flush()
    token = new_secret(32)
    expires = utcnow() + timedelta(minutes=rsvc.QR_MINUTES)
    db.add(QRGrant(consent_id=consent.id, token_hash=sha256_hex(token), expires_at=expires))
    url = f"{get_settings().public_base_url}/scan/{token}"
    img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    await audit(db, "consent.create", actor_type="patient", actor_id=patient.id, subject_type="patient",
                subject_id=patient.id, facility_id=body.facility_id, details={"via": "qr", "scope": body.scope})
    await db.commit()
    return ok(ShareOut(consent_id=consent.id, url=url, expires_at=expires, facility_name=fac.name if fac else None,
                       qr_png="data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()))


@router.delete("/consents/{consent_id}", response_model=Envelope[dict])
async def revoke(consent_id: uuid.UUID, patient: Patient = Depends(current_patient), db: AsyncSession = Depends(get_db)):
    c = await db.get(Consent, consent_id)
    if not c or c.patient_id != patient.id:
        raise AppError(404, "not_found", "Not found")
    now = utcnow()
    c.revoked_at = c.revoked_at or now
    for g in (await db.execute(select(QRGrant).where(QRGrant.consent_id == c.id))).scalars():
        g.revoked_at = g.revoked_at or now
    await audit(db, "consent.revoke", actor_type="patient", actor_id=patient.id, subject_type="patient",
                subject_id=patient.id, facility_id=c.facility_id or c.activated_facility_id)
    await db.commit()
    return ok({"revoked": True})


@router.get("/access-log", response_model=Envelope[AccessLog])
async def access_log(patient: Patient = Depends(current_patient), db: AsyncSession = Depends(get_db)):
    consents = (await db.execute(select(Consent).where(Consent.patient_id == patient.id)
                                 .order_by(Consent.created_at.desc()).limit(50))).scalars().all()
    facs = {f.id: f.name for f in (await db.execute(select(Facility))).scalars()}
    events = (await db.execute(
        select(AuditEvent, User).outerjoin(User, User.id == AuditEvent.actor_id)
        .where(AuditEvent.subject_type == "patient", AuditEvent.subject_id == patient.id,
               AuditEvent.action.in_(LOOK_ACTIONS), AuditEvent.actor_type == "user")
        .order_by(AuditEvent.created_at.desc()).limit(100)
    )).all()
    now = utcnow()
    return ok(AccessLog(
        consents=[ConsentRow(id=c.id, facility_name=facs.get(c.facility_id or c.activated_facility_id), scope=c.scope,
                             via=c.via, created_at=c.created_at, expires_at=c.expires_at, activated_at=c.activated_at,
                             revoked_at=c.revoked_at, active=rsvc.is_live(c, now)) for c in consents],
        events=[LookEvent(at=e.created_at, who=u.full_name if u else None, role=u.role if u else None,
                          facility=facs.get(e.facility_id), what=LOOK_ACTIONS[e.action]) for e, u in events],
    ))


@router.get("/access-requests", response_model=Envelope[list[RequestRow]])
async def access_requests(patient: Patient = Depends(current_patient), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(AccessRequest, Facility.name, User.full_name)
        .join(Facility, Facility.id == AccessRequest.facility_id).join(User, User.id == AccessRequest.requested_by)
        .where(AccessRequest.patient_id == patient.id, AccessRequest.status == "pending",
               AccessRequest.expires_at > utcnow())
        .order_by(AccessRequest.created_at.desc())
    )).all()
    return ok([RequestRow(id=r.id, facility_name=f, requested_by=u, purpose=r.purpose, created_at=r.created_at,
                          expires_at=r.expires_at) for r, f, u in rows])


@router.post("/access-requests/{request_id}", response_model=Envelope[dict])
async def decide_request(request_id: uuid.UUID, body: DecideIn, patient: Patient = Depends(current_patient),
                         db: AsyncSession = Depends(get_db)):
    r = await db.get(AccessRequest, request_id)
    if not r or r.patient_id != patient.id:
        raise AppError(404, "not_found", "Not found")
    if r.status != "pending" or r.expires_at <= utcnow():
        raise AppError(409, "request_closed", "This request is no longer open")
    r.status, r.decided_at = ("approved" if body.decision == "allow" else "denied"), utcnow()
    if body.decision == "allow":
        c = rsvc.new_consent(patient.id, r.facility_id, via="access_request", purpose=r.purpose)
        db.add(c)
        await db.flush()
        r.consent_id = c.id
    await audit(db, f"access.{r.status}", actor_type="patient", actor_id=patient.id, subject_type="patient",
                subject_id=patient.id, facility_id=r.facility_id)
    await db.commit()
    from app.realtime.broker import broker

    broker.publish(f"facility:{r.facility_id}", "access.decided", {"patient_id": patient.id, "status": r.status})
    return ok({"status": r.status})


@router.post("/referrals/{referral_id}/share", response_model=Envelope[ConsentRow])
async def share_with_referral(referral_id: uuid.UUID, patient: Patient = Depends(current_patient),
                              db: AsyncSession = Depends(get_db)):
    """One tap on the referral screen: let the receiving hospital see records from other hospitals for 24 hours."""
    ref = await db.get(Referral, referral_id)
    if not ref or ref.patient_id != patient.id:
        raise AppError(404, "not_found", "Not found")
    c = rsvc.new_consent(patient.id, ref.facility_id, via="referral", purpose="Referral")
    db.add(c)
    await audit(db, "consent.create", actor_type="patient", actor_id=patient.id, subject_type="patient",
                subject_id=patient.id, facility_id=ref.facility_id, details={"via": "referral"})
    await db.commit()
    fac = await db.get(Facility, ref.facility_id)
    return ok(ConsentRow(id=c.id, facility_name=fac.name if fac else None, scope=c.scope, via=c.via,
                         created_at=c.created_at, expires_at=c.expires_at, activated_at=c.activated_at,
                         revoked_at=None, active=True))
