"""Verification decisions for facilities, frontline workers and hospital staff."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.db import utcnow
from app.core.errors import AppError
from app.models import Facility, Upload, User, Verification
from app.models.enums import Role, VerificationStatus
from app.schemas.registration import UploadOut, VerificationOut

S = VerificationStatus
ALLOWED = {
    "approve": {S.pending, S.suspended},
    "reject": {S.pending},
    "suspend": {S.approved},
}
TARGET = {"approve": S.approved, "reject": S.rejected, "suspend": S.suspended}


async def decide(db: AsyncSession, v: Verification, decision: str, reason: str | None, reviewer: User) -> None:
    if v.status not in ALLOWED[decision]:
        raise AppError(409, "invalid_transition", f"Cannot {decision} a {v.status} verification")
    reason = (reason or "").strip() or None
    if decision in ("reject", "suspend") and not reason:
        raise AppError(422, "reason_required", "A reason is required")
    target = TARGET[decision]
    v.status = target
    v.reason = reason
    v.reviewer_id = reviewer.id
    v.decided_at = utcnow()

    if v.subject_type == "facility":
        fac = await db.get(Facility, v.subject_facility_id)
        if not fac:
            raise AppError(404, "not_found", "Facility not found")
        fac.status = target
        fac.status_reason = reason
        # The facility admin account rises and falls with the facility registration.
        if v.subject_user_id:
            admin = await db.get(User, v.subject_user_id)
            if admin and admin.role == Role.facility_admin:
                admin.status = target
                admin.status_reason = reason
    else:
        user = await db.get(User, v.subject_user_id)
        if not user:
            raise AppError(404, "not_found", "User not found")
        user.status = target
        user.status_reason = reason

    await audit(
        db,
        f"verification.{decision}",
        actor_id=reviewer.id,
        subject_type=v.subject_type,
        subject_id=v.subject_facility_id if v.subject_type == "facility" else v.subject_user_id,
        facility_id=v.subject_facility_id,
        details={"verification_id": str(v.id), "reason": reason} if reason else {"verification_id": str(v.id)},
    )


async def serialize(db: AsyncSession, v: Verification) -> VerificationOut:
    user = await db.get(User, v.subject_user_id) if v.subject_user_id else None
    fac = await db.get(Facility, v.subject_facility_id) if v.subject_facility_id else None
    reviewer = await db.get(User, v.reviewer_id) if v.reviewer_id else None
    ids = [uuid.UUID(x) for x in (v.documents or [])]
    docs = (await db.execute(select(Upload).where(Upload.id.in_(ids)))).scalars().all() if ids else []
    return VerificationOut(
        id=v.id,
        subject_type=v.subject_type,
        status=v.status,
        created_at=v.created_at,
        decided_at=v.decided_at,
        reason=v.reason,
        reviewer_name=reviewer.full_name if reviewer else None,
        user_id=user.id if user else None,
        user_name=user.full_name if user else None,
        user_email=user.email if user else None,
        user_role=user.role if user else None,
        facility_id=fac.id if fac else None,
        facility_name=fac.name if fac else None,
        facility_lga=fac.lga if fac else None,
        facility_type=fac.type if fac else None,
        details=v.details or {},
        documents=[
            UploadOut(id=d.id, original_name=d.original_name, content_type=d.content_type, size_bytes=d.size_bytes)
            for d in docs
        ],
    )


async def latest_for_user(db: AsyncSession, user_id: uuid.UUID) -> Verification | None:
    return (
        await db.execute(
            select(Verification)
            .where(Verification.subject_user_id == user_id)
            .order_by(Verification.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
