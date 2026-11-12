"""Network admin: verify facilities and workers, view documents, audit log, network counts (no patient names)."""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.db import get_db
from app.core.deps import current_user, require_roles
from app.core.errors import AppError, Envelope, PageMeta, ok
from app.models import AuditEvent, Facility, Referral, TriageReport, Upload, User, Verification
from app.models.enums import ReferralStatus, Role, VerificationStatus
from app.schemas.registration import DecisionIn, VerificationOut
from app.services import verification as vsvc
from app.services.uploads import path_for

router = APIRouter(prefix="/admin", tags=["admin"])
network_admin = require_roles(Role.network_admin)


@router.get("/verifications", response_model=Envelope[list[VerificationOut]])
async def list_verifications(
    status: Literal["pending", "approved", "rejected", "suspended", "all"] = "pending",
    kind: Literal["facility", "worker", "all"] = "all",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(network_admin),
    db: AsyncSession = Depends(get_db),
):
    """Facilities and frontline workers. Hospital staff are verified by their own facility admin."""
    q = select(Verification).where(Verification.subject_type.in_(["facility", "worker"]))
    if kind != "all":
        q = q.where(Verification.subject_type == kind)
    if status != "all":
        q = q.where(Verification.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.order_by(Verification.created_at.desc()).limit(limit).offset(offset))).scalars()
    return ok([await vsvc.serialize(db, v) for v in rows], PageMeta(total=total, limit=limit, offset=offset))


@router.get("/verifications/{verification_id}", response_model=Envelope[VerificationOut])
async def get_verification(
    verification_id: uuid.UUID, _: User = Depends(network_admin), db: AsyncSession = Depends(get_db)
):
    v = await db.get(Verification, verification_id)
    if not v or v.subject_type == "staff":
        raise AppError(404, "not_found", "Not found")
    return ok(await vsvc.serialize(db, v))


@router.patch("/verifications/{verification_id}", response_model=Envelope[VerificationOut])
async def decide_verification(
    verification_id: uuid.UUID,
    body: DecisionIn,
    admin: User = Depends(network_admin),
    db: AsyncSession = Depends(get_db),
):
    v = await db.get(Verification, verification_id)
    if not v or v.subject_type == "staff":
        raise AppError(404, "not_found", "Not found")
    await vsvc.decide(db, v, body.decision, body.reason, admin)
    await db.commit()
    return ok(await vsvc.serialize(db, v))


async def _can_view_document(db: AsyncSession, user: User, up: Upload) -> bool:
    if user.role == Role.network_admin:
        return True
    if user.role == Role.facility_admin and user.facility_id:
        # Only documents attached to staff verifications at their own facility.
        v = (
            await db.execute(
                select(Verification.id).where(
                    Verification.subject_type == "staff",
                    Verification.subject_facility_id == user.facility_id,
                    Verification.subject_user_id == up.owner_user_id,
                )
            )
        ).first()
        return v is not None
    return False


@router.get("/documents/{upload_id}")
async def get_document(upload_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    up = await db.get(Upload, upload_id)
    if not up or not await _can_view_document(db, user, up):
        raise AppError(404, "not_found", "Not found")
    await audit(db, "document.view", actor_id=user.id, subject_type="upload", subject_id=up.id,
                facility_id=up.facility_id)
    await db.commit()
    return FileResponse(
        path_for(up),
        media_type=up.content_type,
        filename=up.original_name,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store", "Content-Security-Policy": "sandbox; default-src 'none'"},
    )


# ---------- audit ----------
class AuditOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    action: str
    actor_type: str
    actor_id: uuid.UUID | None
    actor_name: str | None
    subject_type: str | None
    subject_id: uuid.UUID | None
    facility_id: uuid.UUID | None
    facility_name: str | None
    details: dict | None
    request_id: str | None


@router.get("/audit", response_model=Envelope[list[AuditOut]])
async def audit_log(
    action: str | None = Query(None, max_length=64),
    actor_id: uuid.UUID | None = None,
    facility_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(network_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(AuditEvent)
    if action:
        q = q.where(AuditEvent.action.startswith(action))
    if actor_id:
        q = q.where(AuditEvent.actor_id == actor_id)
    if facility_id:
        q = q.where(AuditEvent.facility_id == facility_id)
    if since:
        q = q.where(AuditEvent.created_at >= since)
    if until:
        q = q.where(AuditEvent.created_at <= until)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset))).scalars().all()
    users = {u.id: u.full_name for u in (await db.execute(
        select(User).where(User.id.in_({r.actor_id for r in rows if r.actor_id and r.actor_type == "user"}))
    )).scalars()}
    facs = {f.id: f.name for f in (await db.execute(
        select(Facility).where(Facility.id.in_({r.facility_id for r in rows if r.facility_id}))
    )).scalars()}
    out = [
        AuditOut(
            id=r.id, created_at=r.created_at, action=r.action, actor_type=r.actor_type, actor_id=r.actor_id,
            # Patients are never named: show the actor type only.
            actor_name=users.get(r.actor_id) if r.actor_type == "user" else None,
            subject_type=r.subject_type, subject_id=r.subject_id, facility_id=r.facility_id,
            facility_name=facs.get(r.facility_id), details=r.details, request_id=r.request_id,
        )
        for r in rows
    ]
    return ok(out, PageMeta(total=total, limit=limit, offset=offset))


# ---------- metrics ----------
class Metrics(BaseModel):
    triage_reports: int
    red_flags: int
    referrals: int
    referrals_accepted: int
    referrals_declined: int
    median_acceptance_seconds: float | None
    arrival_rate: float | None  # arrived (incl. completed) / accepted-ever
    overdue_now: int
    facilities_approved: int
    facilities_pending: int
    workers_approved: int
    workers_pending: int


@router.get("/metrics", response_model=Envelope[Metrics])
async def metrics(_: User = Depends(network_admin), db: AsyncSession = Depends(get_db)):
    async def count(q) -> int:
        return (await db.execute(q)).scalar_one()

    accepted_ever = Referral.accepted_at.is_not(None)
    med = (
        await db.execute(
            select(
                func.percentile_cont(0.5).within_group(
                    func.extract("epoch", Referral.accepted_at - Referral.created_at)
                )
            ).where(accepted_ever)
        )
    ).scalar_one()
    n_accepted = await count(select(func.count()).select_from(Referral).where(accepted_ever))
    n_arrived = await count(select(func.count()).select_from(Referral).where(Referral.arrived_at.is_not(None)))
    return ok(
        Metrics(
            triage_reports=await count(select(func.count()).select_from(TriageReport)),
            red_flags=await count(select(func.count()).select_from(TriageReport).where(TriageReport.red_flag)),
            referrals=await count(select(func.count()).select_from(Referral)),
            referrals_accepted=n_accepted,
            referrals_declined=await count(
                select(func.count()).select_from(Referral).where(Referral.status == ReferralStatus.declined)
            ),
            median_acceptance_seconds=float(med) if med is not None else None,
            arrival_rate=round(n_arrived / n_accepted, 3) if n_accepted else None,
            overdue_now=await count(
                select(func.count()).select_from(Referral).where(Referral.status == ReferralStatus.overdue)
            ),
            facilities_approved=await count(
                select(func.count()).select_from(Facility).where(Facility.status == VerificationStatus.approved)
            ),
            facilities_pending=await count(
                select(func.count()).select_from(Facility).where(Facility.status == VerificationStatus.pending)
            ),
            workers_approved=await count(
                select(func.count()).select_from(User).where(
                    User.role == Role.worker, User.status == VerificationStatus.approved
                )
            ),
            workers_pending=await count(
                select(func.count()).select_from(User).where(
                    User.role == Role.worker, User.status == VerificationStatus.pending
                )
            ),
        )
    )
