import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import request_id_var
from app.models import AuditEvent


async def audit(
    db: AsyncSession,
    action: str,
    *,
    actor_type: str = "user",
    actor_id: uuid.UUID | None = None,
    subject_type: str | None = None,
    subject_id: uuid.UUID | None = None,
    facility_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Adds an audit event to the session. Caller commits. Never put patient PII in details."""
    db.add(
        AuditEvent(
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            subject_type=subject_type,
            subject_id=subject_id,
            facility_id=facility_id,
            details=details,
            request_id=request_id_var.get(),
        )
    )
