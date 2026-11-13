"""Referral state machine, decline -> next facility, arrival, overdue."""

import logging
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.config import get_settings
from app.core.db import utcnow
from app.core.errors import AppError
from app.engines.matching.engine import Match, match
from app.engines.matching.loader import load_snapshots
from app.models import Facility, Patient, Referral, TriageReport, User
from app.models.enums import REFERRAL_TRANSITIONS, ReferralStatus, TriageStatus
from app.realtime.broker import broker
from app.services import push
from app.services.notify import sms
from app.services.triage import report_location

log = logging.getLogger("vitalis.referrals")

OPEN_STATUSES = {ReferralStatus.pending, ReferralStatus.more_info, ReferralStatus.accepted, ReferralStatus.overdue}
TIMESTAMP_FIELD = {
    ReferralStatus.accepted: "accepted_at",
    ReferralStatus.declined: "declined_at",
    ReferralStatus.more_info: "more_info_at",
    ReferralStatus.cancelled: "cancelled_at",
    ReferralStatus.arrived: "arrived_at",
    ReferralStatus.overdue: "overdue_at",
    ReferralStatus.completed: "completed_at",
}


def transition(ref: Referral, to: ReferralStatus) -> None:
    current = ReferralStatus(ref.status)
    if to not in REFERRAL_TRANSITIONS[current]:
        raise AppError(409, "invalid_transition", f"Cannot go from {current} to {to}")
    ref.status = to
    setattr(ref, TIMESTAMP_FIELD[to], utcnow())


async def _ranked(db: AsyncSession, report: TriageReport) -> list[Match]:
    lat, lng, _ = report_location(report)
    snaps = await load_snapshots(db, report.id)
    return match(snaps, report.care_type, lat, lng, utcnow(), get_settings().city_speed_kmh, limit=50).matches


async def _tried_facilities(db: AsyncSession, report_id: uuid.UUID) -> set[uuid.UUID]:
    return set(
        (await db.execute(select(Referral.facility_id).where(Referral.report_id == report_id))).scalars()
    )


def publish(ref: Referral, event: str, extra: dict | None = None) -> None:
    data = {"referral_id": ref.id, "report_id": ref.report_id, "status": ref.status, **(extra or {})}
    broker.publish(f"referral:{ref.id}", event, data)
    broker.publish(f"report:{ref.report_id}", event, data)
    broker.publish(f"facility:{ref.facility_id}", event, data)
    if ref.worker_id:
        broker.publish(f"worker:{ref.worker_id}", event, data)


async def create_referral(
    db: AsyncSession,
    report: TriageReport,
    facility_id: uuid.UUID | None,
    *,
    worker_id: uuid.UUID | None = None,
    previous: Referral | None = None,
) -> Referral | None:
    # One open referral per report.
    open_ref = (
        await db.execute(
            select(Referral).where(Referral.report_id == report.id, Referral.status.in_(OPEN_STATUSES))
        )
    ).scalar_one_or_none()
    if open_ref and previous is None:
        return open_ref

    ranked = await _ranked(db, report)
    tried = await _tried_facilities(db, report.id)
    if facility_id:
        choice = next((m for m in ranked if m.facility_id == facility_id), None)
        if choice is None:
            raise AppError(422, "facility_not_suitable", "That facility cannot take this patient right now")
    else:
        choice = next((m for m in ranked if m.facility_id not in tried), None)
        if choice is None:
            return None
    rank = next(i for i, m in enumerate(ranked, start=1) if m.facility_id == choice.facility_id)

    ref = Referral(
        report_id=report.id,
        patient_id=report.patient_id,
        facility_id=choice.facility_id,
        worker_id=worker_id or report.worker_id,
        previous_referral_id=previous.id if previous else None,
        status=ReferralStatus.pending,
        rank=rank,
        score=choice.score,
        distance_km=choice.distance_km,
        eta_minutes=choice.eta_minutes,
        care_type=report.care_type,
        heads_up=report.heads_up_sent_at is not None,
    )
    db.add(ref)
    report.status = TriageStatus.referred
    await db.flush()
    publish(ref, "referral.new", {"facility_name": choice.name})
    await push.notify_facility(
        db, ref.facility_id, {"receptionist", "doctor", "facility_admin", "nurse"},
        title="New referral" + (" · emergency" if report.red_flag else ""),
        body="A patient is being referred to you" + (f", about {ref.eta_minutes} min away." if ref.eta_minutes else "."),
        url="/hospital", tag=f"ref-{ref.id}",
    )
    return ref


async def decide(
    db: AsyncSession, ref: Referral, action: str, reason: str | None, user_id: uuid.UUID
) -> Referral | None:
    """Returns the next referral if a decline auto-offered another facility."""
    target = {
        "accept": ReferralStatus.accepted,
        "decline": ReferralStatus.declined,
        "more_info": ReferralStatus.more_info,
    }.get(action)
    if target is None:
        raise AppError(422, "validation_error", "Unknown action")
    if target in (ReferralStatus.declined, ReferralStatus.more_info) and not (reason or "").strip():
        raise AppError(422, "reason_required", "A reason is required")
    transition(ref, target)
    ref.decision_reason = (reason or "").strip() or None
    ref.decided_by = user_id
    await audit(
        db,
        f"referral.{action}",
        actor_id=user_id,
        subject_type="referral",
        subject_id=ref.id,
        facility_id=ref.facility_id,
        details={"reason": ref.decision_reason} if ref.decision_reason else None,
    )

    nxt = None
    if target == ReferralStatus.declined:
        report = await db.get(TriageReport, ref.report_id)
        assert report is not None
        nxt = await create_referral(db, report, None, previous=ref)
    await db.flush()
    publish(ref, f"referral.{ref.status}", {"next_referral_id": nxt.id if nxt else None})
    await _text_family(db, ref, target, nxt)
    return nxt


async def _text_family(db: AsyncSession, ref: Referral, target: ReferralStatus, nxt: Referral | None) -> None:
    """SMS the family (phone given at triage) and the referring worker. No clinical details, ever."""
    if target not in (ReferralStatus.accepted, ReferralStatus.declined):
        return
    patient = await db.get(Patient, ref.patient_id)
    facility = await db.get(Facility, ref.facility_id)
    if not patient or not facility:
        return
    if target == ReferralStatus.accepted:
        eta = f" in about {ref.eta_minutes} min" if ref.eta_minutes else ""
        msg = (f"VITALIS: {facility.name} is ready for {patient.vitalis_id} and expects you{eta}. "
               "Show this ID at reception. Emergency: call 112.")
    else:
        other = await db.get(Facility, nxt.facility_id) if nxt else None
        msg = (f"VITALIS: {facility.name} cannot take {patient.vitalis_id} now. "
               + (f"We have asked {other.name}. Wait for their answer." if other
                  else "Go to the nearest hospital or call 112."))
    worker = await db.get(User, ref.worker_id) if ref.worker_id else None
    for phone in {p for p in (patient.phone, worker.phone if worker else None) if p}:
        await sms().send(phone, msg)
    await _push_both(db, ref, nxt, "Hospital is ready" if target == ReferralStatus.accepted else "Finding another hospital",
                     msg.removeprefix("VITALIS: "))


async def _push_both(db: AsyncSession, ref: Referral, nxt: Referral | None, title: str, body: str) -> None:
    """Family's phone opens their referral page; the chemist's opens it in their worker app."""
    target = nxt or ref
    await push.notify(db, patient_ids=[ref.patient_id], title=title, body=body, url=f"/referral/{target.id}",
                      tag=f"ref-{ref.report_id}")
    if ref.worker_id:
        await push.notify(db, user_ids=[ref.worker_id], title=title, body=body,
                          url=f"/worker/referrals/{target.id}", tag=f"ref-{ref.report_id}")


async def mark_arrived(db: AsyncSession, ref: Referral, user_id: uuid.UUID) -> None:
    transition(ref, ReferralStatus.arrived)
    await audit(
        db, "referral.arrived", actor_id=user_id, subject_type="referral", subject_id=ref.id,
        facility_id=ref.facility_id,
    )
    publish(ref, "referral.arrived")


def overdue_deadline(ref: Referral):
    assert ref.accepted_at is not None
    return ref.accepted_at + timedelta(
        minutes=(ref.eta_minutes or 0) + get_settings().overdue_grace_minutes
    )


async def run_overdue_check(db: AsyncSession) -> int:
    """Marks accepted referrals overdue when now > accepted_at + ETA + grace. Returns count."""
    now = utcnow()
    rows = (
        await db.execute(select(Referral).where(Referral.status == ReferralStatus.accepted))
    ).scalars().all()
    count = 0
    for ref in rows:
        if now <= overdue_deadline(ref):
            continue
        transition(ref, ReferralStatus.overdue)
        count += 1
        patient = await db.get(Patient, ref.patient_id)
        facility = await db.get(Facility, ref.facility_id)
        await audit(db, "referral.overdue", actor_type="system", subject_type="referral", subject_id=ref.id,
                    facility_id=ref.facility_id)
        publish(ref, "referral.overdue")
        worker = await db.get(User, ref.worker_id) if ref.worker_id else None
        if worker and worker.phone and facility and patient:
            await sms().send(
                worker.phone,
                f"VITALIS: your referral {patient.vitalis_id} to {facility.name} is overdue. Please check on them.",
            )
        if patient and patient.phone and facility:
            await sms().send(
                patient.phone,
                f"VITALIS: {patient.vitalis_id} has not arrived at {facility.name}. "
                "If you are on the way, keep going. If you need help, call 112.",
            )
        if patient and facility:
            await _push_both(db, ref, None, "Not arrived yet",
                             f"{patient.vitalis_id} has not arrived at {facility.name}. If you need help, call 112.")
    await db.commit()
    return count
