import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import current_patient
from app.core.errors import Envelope, ok
from app.core.ratelimit import limiter, patient_key
from app.engines.triage.data import care_types, symptoms
from app.models import Patient, Referral, TriageReport
from app.schemas.triage import (
    ExcludedCard,
    HospitalCard,
    HospitalSummary,
    RedFlagOut,
    TapsIn,
    Taxonomy,
    TriageOut,
    TriageStartIn,
)
from app.services import triage as svc
from app.services.referrals import OPEN_STATUSES

router = APIRouter(prefix="/triage", tags=["triage"])


async def _active_referral_id(db: AsyncSession, report_id: uuid.UUID) -> uuid.UUID | None:
    return (
        await db.execute(
            select(Referral.id)
            .where(Referral.report_id == report_id, Referral.status.in_(OPEN_STATUSES | {"arrived"}))
            .order_by(Referral.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


def to_out(ev: svc.Evaluation, active_referral_id: uuid.UUID | None = None) -> TriageOut:
    r = ev.report
    ct_cfg = care_types()["care_types"].get(ev.care_type or "", {})
    m = ev.matches
    return TriageOut(
        report_id=r.id,
        status=r.status,
        red_flag=RedFlagOut(fired=ev.rf.fired, message=r.red_flag_message),
        care_type=ev.care_type,
        care_label=ct_cfg.get("label"),
        action_level=ev.action_level,
        self_care_return_if=care_types()["action_rules"]["self_care_return_if"]
        if ev.action_level == "self_care"
        else [],
        what_to_bring=ct_cfg.get("what_to_bring", []),
        heads_up_sent=r.heads_up_sent_at is not None,
        hospitals=HospitalSummary(
            nearby=m.nearby,
            can_handle=m.can_handle,
            ready_now=m.ready_now,
            top=[
                HospitalCard(
                    facility_id=x.facility_id, name=x.name, lga=x.lga, lat=x.lat, lng=x.lng, phone=x.phone,
                    distance_km=x.distance_km, eta_minutes=x.eta_minutes, score=x.score,
                    freshness=x.freshness, last_confirmed_at=x.last_confirmed_at, ready_now=x.ready_now,
                    reasons=x.reasons, warnings=x.warnings,
                )
                for x in m.matches[:3]
            ],
            excluded=[
                ExcludedCard(facility_id=e.facility_id, name=e.name, distance_km=e.distance_km, reasons=e.reasons)
                for e in m.excluded[:5]
            ],
            approximate_location=ev.approx_location,
        ),
        context=r.context or {},
        answers=r.answers or {},
        active_referral_id=active_referral_id,
    )


@router.get("/taxonomy", response_model=Envelope[Taxonomy])
async def taxonomy():
    """Public UI taxonomy (regions, symptoms, emergencies, who, severity, onset). No model codes."""
    return ok(Taxonomy.model_validate({**symptoms(), "lgas": svc.lgas()["lgas"]}))


@router.post("", response_model=Envelope[TriageOut])
@limiter.limit("30/minute", key_func=patient_key)
async def start_triage(
    request: Request,
    body: TriageStartIn,
    patient: Patient = Depends(current_patient),
    db: AsyncSession = Depends(get_db),
):
    ctx = {k: v for k, v in {"age_group": patient.age_group, "sex": patient.sex}.items() if v}
    if patient.pregnant:
        ctx["pregnant"] = True
    r = TriageReport(patient_id=patient.id, context=ctx, answers={"symptoms": [], "regions": []})
    db.add(r)
    await db.flush()
    await svc.record_taps(db, r, [t.model_dump(exclude_none=True) for t in body.taps])
    ev = await svc.evaluate(db, r)
    out = to_out(ev)
    await db.commit()
    return ok(out)


@router.post("/{report_id}/taps", response_model=Envelope[TriageOut])
@limiter.limit("120/minute", key_func=patient_key)
async def taps(
    request: Request,
    report_id: uuid.UUID,
    body: TapsIn,
    patient: Patient = Depends(current_patient),
    db: AsyncSession = Depends(get_db),
):
    r = await svc.get_report_for_patient(db, report_id, patient.id)
    await svc.record_taps(db, r, [t.model_dump(exclude_none=True) for t in body.taps])
    ev = await svc.evaluate(db, r)
    out = to_out(ev, await _active_referral_id(db, r.id))
    await db.commit()
    return ok(out)


@router.get("/{report_id}", response_model=Envelope[TriageOut])
async def get_triage(
    report_id: uuid.UUID, patient: Patient = Depends(current_patient), db: AsyncSession = Depends(get_db)
):
    r = await svc.get_report_for_patient(db, report_id, patient.id)
    active = await _active_referral_id(db, r.id)
    ev = await svc.evaluate(db, r, call_model=False)
    out = to_out(ev, active)
    await db.rollback()  # read-only view
    return ok(out)
