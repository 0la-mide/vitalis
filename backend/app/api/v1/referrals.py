"""Patient-facing referral endpoints (X-Patient-Key)."""

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.db import get_db
from app.core.deps import current_patient
from app.core.errors import AppError, Envelope, ok
from app.core.ratelimit import limiter, patient_key
from app.engines.triage.data import care_types
from app.models import Facility, Patient, Referral
from app.realtime.broker import SSE_HEADERS, broker
from app.schemas.referral import FacilityPublic, ReferralCreateIn, ReferralPatientOut
from app.services import referrals as svc
from app.services.triage import get_report_for_patient

router = APIRouter(tags=["referral"])


def directions_url(lat: float, lng: float) -> str:
    return f"https://www.openstreetmap.org/directions?to={lat:.5f}%2C{lng:.5f}#map=15/{lat:.5f}/{lng:.5f}"


async def patient_view(db: AsyncSession, ref: Referral, patient: Patient) -> ReferralPatientOut:
    f = await db.get(Facility, ref.facility_id)
    assert f is not None
    nxt = (
        await db.execute(select(Referral.id).where(Referral.previous_referral_id == ref.id))
    ).scalar_one_or_none()
    prev_name = None
    if ref.previous_referral_id:
        prev = await db.get(Referral, ref.previous_referral_id)
        pf = await db.get(Facility, prev.facility_id) if prev else None
        prev_name = pf.name if pf else None
    ct = care_types()["care_types"].get(ref.care_type or "", {})
    return ReferralPatientOut(
        id=ref.id,
        report_id=ref.report_id,
        status=ref.status,
        facility=FacilityPublic(
            id=f.id, name=f.name, lga=f.lga, address=f.address, phone=f.phone, lat=f.lat, lng=f.lng
        ),
        distance_km=ref.distance_km,
        eta_minutes=ref.eta_minutes,
        directions_url=directions_url(f.lat, f.lng),
        what_to_bring=ct.get("what_to_bring", []),
        vitalis_id=patient.vitalis_id,
        # The hospital's internal reason is not shown to the family.
        decline_reason="This hospital cannot take this patient right now." if ref.status == "declined" else None,
        next_referral_id=nxt,
        previous_facility_name=prev_name,
        created_at=ref.created_at,
        accepted_at=ref.accepted_at,
        arrived_at=ref.arrived_at,
        overdue_at=ref.overdue_at,
    )


async def _owned(db: AsyncSession, referral_id: uuid.UUID, patient: Patient) -> Referral:
    ref = await db.get(Referral, referral_id)
    if not ref or ref.patient_id != patient.id:
        raise AppError(404, "not_found", "Referral not found")
    return ref


@router.post("/triage/{report_id}/referral", response_model=Envelope[ReferralPatientOut])
@limiter.limit("20/minute", key_func=patient_key)
async def request_referral(
    request: Request,
    report_id: uuid.UUID,
    body: ReferralCreateIn,
    patient: Patient = Depends(current_patient),
    db: AsyncSession = Depends(get_db),
):
    report = await get_report_for_patient(db, report_id, patient.id)
    ref = await svc.create_referral(db, report, body.facility_id)
    if ref is None:
        raise AppError(409, "no_facility", "No suitable hospital is available. Call 112.")
    out = await patient_view(db, ref, patient)
    await db.commit()
    return ok(out)


@router.get("/referrals/{referral_id}", response_model=Envelope[ReferralPatientOut])
async def get_referral(
    referral_id: uuid.UUID, patient: Patient = Depends(current_patient), db: AsyncSession = Depends(get_db)
):
    ref = await _owned(db, referral_id, patient)
    return ok(await patient_view(db, ref, patient))


@router.get("/referrals/{referral_id}/stream")
async def stream_referral(
    referral_id: uuid.UUID, patient: Patient = Depends(current_patient), db: AsyncSession = Depends(get_db)
):
    ref = await _owned(db, referral_id, patient)
    channel = f"report:{ref.report_id}"
    await db.close()
    return EventSourceResponse(broker.subscribe(channel), ping=None, headers=SSE_HEADERS)
