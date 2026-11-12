import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, utcnow


class Consent(IdMixin, Base):
    """The patient lets one facility (or any verified facility) read their record from other hospitals, for a while.

    scope: "full" (visits, vitals, results, signed notes, prescriptions, history) or "summary" (history entries only).
    """

    __tablename__ = "consents"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("facilities.id"), index=True)  # None = any
    scope: Mapped[str] = mapped_column(String(12), default="full")
    via: Mapped[str] = mapped_column(String(16))  # qr | referral | access_request
    purpose: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    activated_at: Mapped[datetime | None]  # QR consents become active when a facility redeems the code
    activated_facility_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("facilities.id"))


class QRGrant(IdMixin, Base):
    """A 10-minute, single-use code shown as a QR. Only the SHA-256 of the token is stored."""

    __tablename__ = "qr_grants"

    consent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consents.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime]
    redeemed_at: Mapped[datetime | None]
    redeemed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    revoked_at: Mapped[datetime | None]


class AccessRequest(IdMixin, Base):
    """A hospital asks to see the record; the patient taps Allow or Deny on their own (device-key authenticated) phone."""

    __tablename__ = "access_requests"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    purpose: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending | approved | denied | expired
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime]
    decided_at: Mapped[datetime | None]
    consent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("consents.id"))
