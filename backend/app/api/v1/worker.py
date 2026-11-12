"""Frontline worker app: triage on behalf of a walk-in, vitals, referrals. Scoped to the worker's own reports."""

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.v1.referrals import directions_url
from app.api.v1.triage import _active_referral_id, to_out
from app.core.audit import audit
from app.core.db import get_db, utcnow
from app.core.deps import require_roles
from app.core.errors import AppError, Envelope, ok
from app.core.ratelimit import limiter
from app.engines.triage.data import care_types
from app.models import Facility, Patient, Referral, TriageReport, User, Vital, WorkerProfile
from app.models.enums import Role
from app.realtime.broker import SSE_HEADERS, broker
from app.schemas.referral import ReferralCreateIn
from app.schemas.triage import TapsIn, TriageOut
from app.schemas.worker import (
    VITAL_RANGES,
    VitalsIn,
    WorkerReferralOut,
    WorkerTriageIn,
    WorkerTriageStartOut,
)
from app.services import referrals as rsvc
from app.services import triage as svc
from app.services.patients import create_patient

router = APIRouter(prefix="/worker", tags=["worker"])
worker_only = require_roles(Role.worker)


async def _own_report(db: AsyncSession, report_id: uuid.UUID, worker: User) -> TriageReport:
    r = await db.get(TriageReport, report_id)
    if not r or r.worker_id != worker.id:
        raise AppError(404, "not_found", "Triage report not found")
    return r


async def _evaluate_out(db: AsyncSession, r: TriageReport, *, call_model: bool = True) -> TriageOut:
    ev = await svc.evaluate(db, r, call_model=call_model)
    return to_out(ev, await _active_referral_id(db, r.id))


@router.post("/triage", response_model=Envelope[WorkerTriageStartOut])
@limiter.limit("60/hour")
async def start(
    request: Request, body: WorkerTriageIn, worker: User = Depends(worker_only), db: AsyncSession = Depends(get_db)
):
    """Creates the walk-in patient and a triage report labelled as done on their behalf."""
    patient, _device_key, recovery = await create_patient(db, phone=body.family_phone, created_by_worker_id=worker.id)
    r = TriageReport(patient_id=patient.id, worker_id=worker.id, context={}, answers={"symptoms": [], "regions": []})
    # Default location: the worker's shop, so matching works before any GPS tap.
    profile = (await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == worker.id))).scalar_one_or_none()
    if profile:
        r.lat, r.lng, r.lga = profile.lat, profile.lng, profile.lga
    db.add(r)
    await db.flush()
    await svc.record_taps(db, r, [t.model_dump(exclude_none=True) for t in body.taps])
    out = await _evaluate_out(db, r)
    await audit(db, "worker.triage.start", actor_id=worker.id, subject_type="patient", subject_id=patient.id)
    await db.commit()
    return ok(WorkerTriageStartOut(triage=out, patient_id=patient.id, vitalis_id=patient.vitalis_id,
                                   recovery_code=recovery))


@router.post("/triage/{report_id}/taps", response_model=Envelope[TriageOut])
async def taps(
    report_id: uuid.UUID, body: TapsIn, worker: User = Depends(worker_only), db: AsyncSession = Depends(get_db)
):
    r = await _own_report(db, report_id, worker)
    await svc.record_taps(db, r, [t.model_dump(exclude_none=True) for t in body.taps])
    out = await _evaluate_out(db, r)
    await db.commit()
    return ok(out)


@router.get("/triage/{report_id}", response_model=Envelope[TriageOut])
async def get_triage(report_id: uuid.UUID, worker: User = Depends(worker_only), db: AsyncSession = Depends(get_db)):
    r = await _own_report(db, report_id, worker)
    out = await _evaluate_out(db, r, call_model=False)
    await db.rollback()
    return ok(out)


@router.post("/patients/{patient_id}/vitals", response_model=Envelope[TriageOut])
async def add_vitals(
    patient_id: uuid.UUID, body: VitalsIn, worker: User = Depends(worker_only), db: AsyncSession = Depends(get_db)
):
    """Records vitals (units fixed per kind) and re-runs the red-flag rules immediately."""
    r = await _own_report(db, body.report_id, worker)
    if r.patient_id != patient_id:
        raise AppError(404, "not_found", "Not found")
    now = utcnow()
    for reading in body.readings:
        lo, hi, unit = VITAL_RANGES[reading.kind]
        if not lo <= reading.value <= hi:
            raise AppError(422, "vital_out_of_range", f"{reading.kind} must be between {lo:g} and {hi:g} {unit}",
                           {"kind": reading.kind})
        measured = reading.measured_at or now
        if measured > now + timedelta(minutes=5):
            raise AppError(422, "validation_error", "Measurement time is in the future")
        db.add(Vital(patient_id=patient_id, report_id=r.id, source="worker", kind=reading.kind, value=reading.value,
                     unit=unit, measured_at=measured, entered_by=worker.id))
    await db.flush()
    out = await _evaluate_out(db, r, call_model=False)
    await audit(db, "worker.vitals", actor_id=worker.id, subject_type="patient", subject_id=patient_id,
                details={"kinds": [x.kind for x in body.readings]})
    await db.commit()
    return ok(out)


@router.post("/triage/{report_id}/referral", response_model=Envelope[WorkerReferralOut])
async def refer(
    report_id: uuid.UUID, body: ReferralCreateIn, worker: User = Depends(worker_only),
    db: AsyncSession = Depends(get_db),
):
    r = await _own_report(db, report_id, worker)
    ref = await rsvc.create_referral(db, r, body.facility_id, worker_id=worker.id)
    if ref is None:
        raise AppError(409, "no_facility", "No suitable hospital is available. Call 112.")
    out = await _view(db, ref)
    await db.commit()
    return ok(out)


async def _view(db: AsyncSession, ref: Referral) -> WorkerReferralOut:
    f = await db.get(Facility, ref.facility_id)
    p = await db.get(Patient, ref.patient_id)
    r = await db.get(TriageReport, ref.report_id)
    assert f and p and r
    nxt = (await db.execute(select(Referral.id).where(Referral.previous_referral_id == ref.id))).scalar_one_or_none()
    prev_name = None
    if ref.previous_referral_id:
        prev = await db.get(Referral, ref.previous_referral_id)
        pf = await db.get(Facility, prev.facility_id) if prev else None
        prev_name = pf.name if pf else None
    return WorkerReferralOut(
        id=ref.id, report_id=ref.report_id, status=ref.status, vitalis_id=p.vitalis_id, facility_id=f.id,
        facility_name=f.name, facility_phone=f.phone, facility_lat=f.lat, facility_lng=f.lng,
        care_type=ref.care_type, care_label=care_types()["care_types"].get(ref.care_type or "", {}).get("label"),
        red_flag=r.red_flag, red_flag_message=r.red_flag_message, distance_km=ref.distance_km,
        eta_minutes=ref.eta_minutes, decision_reason=ref.decision_reason, next_referral_id=nxt,
        previous_facility_name=prev_name, directions_url=directions_url(f.lat, f.lng), created_at=ref.created_at,
        accepted_at=ref.accepted_at, declined_at=ref.declined_at, arrived_at=ref.arrived_at,
        overdue_at=ref.overdue_at,
    )


@router.get("/referrals", response_model=Envelope[list[WorkerReferralOut]])
async def my_referrals(worker: User = Depends(worker_only), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Referral)
            .where(Referral.worker_id == worker.id, Referral.created_at >= utcnow() - timedelta(days=7))
            .order_by(Referral.created_at.desc())
        )
    ).scalars().all()
    return ok([await _view(db, ref) for ref in rows])


@router.get("/referrals/stream")
async def stream(worker: User = Depends(worker_only), db: AsyncSession = Depends(get_db)):
    # Release the DB connection before streaming (see hospital stream).
    await db.close()
    return EventSourceResponse(broker.subscribe(f"worker:{worker.id}"), ping=None, headers=SSE_HEADERS)


@router.get("/referrals/{referral_id}", response_model=Envelope[WorkerReferralOut])
async def get_referral(referral_id: uuid.UUID, worker: User = Depends(worker_only), db: AsyncSession = Depends(get_db)):
    ref = await db.get(Referral, referral_id)
    if not ref or ref.worker_id != worker.id:
        raise AppError(404, "not_found", "Not found")
    return ok(await _view(db, ref))
