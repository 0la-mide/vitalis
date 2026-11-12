"""Receiving-hospital endpoints. Every query is scoped to the user's own facility."""

import uuid
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.audit import audit
from app.core.db import get_db, utcnow
from app.core.deps import ensure_same_facility, require_hospital_staff
from app.core.errors import AppError, Envelope, ok
from app.engines.matching.engine import freshness_of
from app.engines.triage.data import care_types, symptom_index
from app.models import (
    FacilityAlert,
    FacilityService,
    Patient,
    Referral,
    Service,
    TriageReport,
    User,
    Verification,
    Vital,
)
from app.models.enums import AlertStatus, Availability, Role
from app.realtime.broker import SSE_HEADERS, broker
from app.schemas.referral import (
    DecisionIn,
    DecisionOut,
    IncomingItem,
    IncomingPatient,
    SymptomLine,
    VitalLine,
)
from app.services import referrals as svc
from app.services import verification as vsvc

router = APIRouter(prefix="/hospital", tags=["hospital"])

any_staff = require_hospital_staff()
deciders = require_hospital_staff(Role.doctor, Role.nurse, Role.facility_admin)
front_desk = require_hospital_staff(Role.receptionist, Role.nurse, Role.facility_admin)

VITAL_UNITS = {"spo2": "%", "systolic_bp": "mmHg", "diastolic_bp": "mmHg", "pulse": "bpm", "temp_c": "°C",
               "resp_rate": "/min", "weight_kg": "kg"}


async def _item(db: AsyncSession, report: TriageReport, *, ref: Referral | None, alert: FacilityAlert | None) -> IncomingItem:
    patient = await db.get(Patient, report.patient_id)
    assert patient is not None
    idx = symptom_index()
    syms = [
        SymptomLine(
            code=s["code"],
            label=idx.get(s["code"], {}).get("labels", {}).get("en", s["code"]),
            region=s.get("region"),
            severity=s.get("severity"),
            onset=s.get("onset"),
        )
        for s in (report.answers or {}).get("symptoms", [])
    ]
    vitals = [
        VitalLine(kind=v.kind, value=v.value, unit=v.unit, source=v.source, measured_at=v.measured_at)
        for v in (
            await db.execute(select(Vital).where(Vital.patient_id == patient.id).order_by(Vital.measured_at.desc()).limit(12))
        ).scalars()
    ]
    referred_by = None
    if report.worker_id:
        w = await db.get(User, report.worker_id)
        referred_by = w.full_name if w else None
    ctx = report.context or {}
    base = dict(
        report_id=report.id,
        patient=IncomingPatient(
            vitalis_id=patient.vitalis_id,
            age_group=ctx.get("age_group") or patient.age_group,
            sex=ctx.get("sex") or patient.sex,
            pregnant=bool(ctx.get("pregnant")),
        ),
        care_type=report.care_type,
        red_flag=report.red_flag,
        red_flag_message=report.red_flag_message,
        symptoms=syms,
        vitals=vitals,
        referred_by=referred_by,
    )
    if ref:
        expected = ref.accepted_at + timedelta(minutes=ref.eta_minutes or 0) if ref.accepted_at else None
        return IncomingItem(
            kind="referral", id=ref.id, status=ref.status, created_at=ref.created_at,
            distance_km=ref.distance_km, eta_minutes=ref.eta_minutes, expected_arrival_at=expected,
            decision_reason=ref.decision_reason, accepted_at=ref.accepted_at, arrived_at=ref.arrived_at,
            overdue_at=ref.overdue_at, **base,
        )
    assert alert is not None
    return IncomingItem(
        kind="alert", id=alert.id, status=alert.status, created_at=alert.created_at, distance_km=None,
        eta_minutes=None, expected_arrival_at=None, decision_reason=None, accepted_at=None, arrived_at=None,
        overdue_at=None, **base,
    )


@router.get("/incoming", response_model=Envelope[list[IncomingItem]])
async def incoming(user: User = Depends(any_staff), db: AsyncSession = Depends(get_db)):
    since = utcnow() - timedelta(hours=24)
    refs = (
        await db.execute(
            select(Referral)
            .where(Referral.facility_id == user.facility_id, Referral.created_at >= since)
            .order_by(Referral.created_at.desc())
        )
    ).scalars().all()
    referred_reports = {r.report_id for r in refs}
    alerts = (
        await db.execute(
            select(FacilityAlert)
            .where(
                FacilityAlert.facility_id == user.facility_id,
                FacilityAlert.created_at >= utcnow() - timedelta(hours=6),
                FacilityAlert.status != AlertStatus.dismissed,
            )
            .order_by(FacilityAlert.created_at.desc())
        )
    ).scalars().all()
    items: list[IncomingItem] = []
    for ref in refs:
        report = await db.get(TriageReport, ref.report_id)
        items.append(await _item(db, report, ref=ref, alert=None))
    for a in alerts:
        if a.report_id in referred_reports:
            continue
        report = await db.get(TriageReport, a.report_id)
        items.append(await _item(db, report, ref=None, alert=a))
    await audit(db, "hospital.incoming.view", actor_id=user.id, facility_id=user.facility_id,
                details={"count": len(items)})
    await db.commit()
    return ok(items)


@router.get("/stream")
async def stream(user: User = Depends(any_staff)):
    return EventSourceResponse(broker.subscribe(f"facility:{user.facility_id}"), ping=None, headers=SSE_HEADERS)


async def _scoped_referral(db: AsyncSession, referral_id: uuid.UUID, user: User) -> Referral:
    ref = await db.get(Referral, referral_id)
    if not ref:
        raise AppError(404, "not_found", "Not found")
    ensure_same_facility(user, ref.facility_id)
    return ref


@router.get("/referrals/{referral_id}", response_model=Envelope[IncomingItem])
async def get_referral(referral_id: uuid.UUID, user: User = Depends(any_staff), db: AsyncSession = Depends(get_db)):
    ref = await _scoped_referral(db, referral_id, user)
    report = await db.get(TriageReport, ref.report_id)
    item = await _item(db, report, ref=ref, alert=None)
    await audit(db, "referral.view", actor_id=user.id, subject_type="referral", subject_id=ref.id,
                facility_id=user.facility_id)
    await db.commit()
    return ok(item)


@router.patch("/referrals/{referral_id}", response_model=Envelope[DecisionOut])
async def decide(
    referral_id: uuid.UUID, body: DecisionIn, user: User = Depends(deciders), db: AsyncSession = Depends(get_db)
):
    ref = await _scoped_referral(db, referral_id, user)
    nxt = await svc.decide(db, ref, body.action, body.reason, user.id)
    out = DecisionOut(referral_id=ref.id, status=ref.status, next_referral_id=nxt.id if nxt else None)
    await db.commit()
    return ok(out)


@router.post("/referrals/{referral_id}/arrived", response_model=Envelope[DecisionOut])
async def arrived(referral_id: uuid.UUID, user: User = Depends(front_desk), db: AsyncSession = Depends(get_db)):
    ref = await _scoped_referral(db, referral_id, user)
    await svc.mark_arrived(db, ref, user.id)
    out = DecisionOut(referral_id=ref.id, status=ref.status, next_referral_id=None)
    await db.commit()
    return ok(out)


@router.post("/alerts/{alert_id}/ready", response_model=Envelope[dict])
async def alert_ready(alert_id: uuid.UUID, user: User = Depends(deciders), db: AsyncSession = Depends(get_db)):
    alert = await db.get(FacilityAlert, alert_id)
    if not alert:
        raise AppError(404, "not_found", "Not found")
    ensure_same_facility(user, alert.facility_id)
    alert.status = AlertStatus.ready
    alert.ready_at = utcnow()
    alert.ready_by = user.id
    await audit(db, "alert.ready", actor_id=user.id, subject_type="alert", subject_id=alert.id,
                facility_id=user.facility_id)
    await db.commit()
    data = {"alert_id": alert.id, "report_id": alert.report_id, "facility_id": alert.facility_id}
    broker.publish(f"report:{alert.report_id}", "alert.ready", data)
    broker.publish(f"facility:{alert.facility_id}", "alert.ready", data)
    return ok({"status": alert.status})


# ---------- availability ----------
class ServiceRow(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    category: str
    availability_status: str
    last_confirmed_at: str | None
    freshness: str


class ServicePatchIn(BaseModel):
    availability_status: Availability


async def _service_rows(db: AsyncSession, facility_id: uuid.UUID) -> list[ServiceRow]:
    rows = (
        await db.execute(
            select(FacilityService, Service)
            .join(Service, Service.code == FacilityService.service_code)
            .where(FacilityService.facility_id == facility_id)
            .order_by(Service.category, Service.name)
        )
    ).all()
    now = utcnow()
    return [
        ServiceRow(
            id=fs.id, code=s.code, name=s.name, category=s.category, availability_status=fs.availability_status,
            last_confirmed_at=fs.last_confirmed_at.isoformat() if fs.last_confirmed_at else None,
            freshness=freshness_of(fs.last_confirmed_at, now),
        )
        for fs, s in rows
    ]


@router.get("/services", response_model=Envelope[list[ServiceRow]])
async def services(user: User = Depends(any_staff), db: AsyncSession = Depends(get_db)):
    return ok(await _service_rows(db, user.facility_id))


@router.patch("/services/{service_id}", response_model=Envelope[list[ServiceRow]])
async def update_service(
    service_id: uuid.UUID, body: ServicePatchIn, user: User = Depends(any_staff), db: AsyncSession = Depends(get_db)
):
    fs = await db.get(FacilityService, service_id)
    if not fs:
        raise AppError(404, "not_found", "Not found")
    ensure_same_facility(user, fs.facility_id)
    fs.availability_status = body.availability_status
    fs.last_confirmed_at = utcnow()
    fs.reported_by = user.id
    await audit(db, "service.update", actor_id=user.id, subject_type="facility_service", subject_id=fs.id,
                facility_id=user.facility_id, details={"code": fs.service_code, "status": body.availability_status})
    await db.commit()
    return ok(await _service_rows(db, user.facility_id))


@router.get("/care-types")
async def care_type_labels(_: User = Depends(any_staff)):
    return ok({k: v["label"] for k, v in care_types()["care_types"].items()})


# ---------- staff approvals (facility admin) ----------
class StaffRow(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    role: str
    status: str
    status_reason: str | None
    licence_number: str | None
    created_at: str
    verification_id: uuid.UUID | None


class StaffDecisionIn(BaseModel):
    decision: Literal["approve", "reject", "suspend"]
    reason: str | None = None


facility_admin_only = require_hospital_staff(Role.facility_admin)


async def _staff_rows(db: AsyncSession, facility_id: uuid.UUID, me: uuid.UUID) -> list[StaffRow]:
    users = (
        await db.execute(
            select(User)
            .where(User.facility_id == facility_id, User.id != me, User.role != Role.facility_admin)
            .order_by(User.status, User.full_name)
        )
    ).scalars().all()
    out = []
    for u in users:
        v = await vsvc.latest_for_user(db, u.id)
        out.append(StaffRow(user_id=u.id, full_name=u.full_name, email=u.email, role=u.role, status=u.status,
                            status_reason=u.status_reason, licence_number=u.licence_number,
                            created_at=u.created_at.isoformat(), verification_id=v.id if v else None))
    return out


@router.get("/staff", response_model=Envelope[list[StaffRow]])
async def staff(user: User = Depends(facility_admin_only), db: AsyncSession = Depends(get_db)):
    return ok(await _staff_rows(db, user.facility_id, user.id))


@router.patch("/staff/{user_id}", response_model=Envelope[list[StaffRow]])
async def decide_staff(
    user_id: uuid.UUID, body: StaffDecisionIn, user: User = Depends(facility_admin_only),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, user_id)
    if not target or target.facility_id != user.facility_id or target.role == Role.facility_admin:
        raise AppError(404, "not_found", "Not found")
    v = await vsvc.latest_for_user(db, target.id)
    if v is None or v.subject_type != "staff":
        # Seeded or legacy accounts without a registration record get one so the decision is recorded.
        v = Verification(subject_type="staff", subject_user_id=target.id, subject_facility_id=user.facility_id,
                         status=target.status, details={"licence_number": target.licence_number})
        db.add(v)
        await db.flush()
    await vsvc.decide(db, v, body.decision, body.reason, user)
    await db.commit()
    return ok(await _staff_rows(db, user.facility_id, user.id))
