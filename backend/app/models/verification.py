import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin, utcnow
from app.models.enums import VerificationStatus


class Upload(IdMixin, Base):
    """A verification document. Stored outside the web root under a random name; served only to reviewers."""

    __tablename__ = "uploads"

    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("facilities.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(32))  # facility_licence | worker_licence | staff_licence
    original_name: Mapped[str] = mapped_column(String(200))
    stored_name: Mapped[str] = mapped_column(String(80), unique=True)
    content_type: Mapped[str] = mapped_column(String(40))
    size_bytes: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Verification(IdMixin, TimestampMixin, Base):
    """One review request. subject_type: facility | worker | staff. Reviewer: network admin or facility admin."""

    __tablename__ = "verifications"

    subject_type: Mapped[str] = mapped_column(String(16), index=True)
    subject_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject_facility_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("facilities.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default=VerificationStatus.pending, index=True)
    documents: Mapped[list] = mapped_column(JSON, default=list)  # upload ids (str)
    details: Mapped[dict] = mapped_column(JSON, default=dict)  # licence numbers etc. at submission time
    reason: Mapped[str | None] = mapped_column(Text)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_at: Mapped[datetime | None]
