import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engines.matching.engine import FacilitySnap, ServiceSnap
from app.models import Facility, FacilityAlert
from app.models.enums import AlertStatus, VerificationStatus


async def load_snapshots(db: AsyncSession, report_id: uuid.UUID | None = None) -> list[FacilitySnap]:
    """Verified facilities only. Unverified facilities never appear in matching."""
    rows = (
        await db.execute(
            select(Facility)
            .where(Facility.status == VerificationStatus.approved)
            .options(selectinload(Facility.services))
        )
    ).scalars().all()
    ready: set[uuid.UUID] = set()
    if report_id:
        ready = set(
            (
                await db.execute(
                    select(FacilityAlert.facility_id).where(
                        FacilityAlert.report_id == report_id,
                        FacilityAlert.status == AlertStatus.ready,
                    )
                )
            ).scalars()
        )
    return [
        FacilitySnap(
            id=f.id,
            name=f.name,
            lga=f.lga,
            type=f.type,
            lat=f.lat,
            lng=f.lng,
            phone=f.phone,
            services={
                s.service_code: ServiceSnap(s.service_code, s.availability_status, s.last_confirmed_at)
                for s in f.services
            },
            ready_alert=f.id in ready,
        )
        for f in rows
    ]
