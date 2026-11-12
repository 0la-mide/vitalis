import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin, utcnow
from app.models.enums import EncounterState


class Encounter(IdMixin, TimestampMixin, Base):
    """A patient's visit at a receiving facility, from arrival to disposition."""

    __tablename__ = "encounters"

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    referral_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("referrals.id"), unique=True)
    report_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("triage_reports.id"))
    state: Mapped[str] = mapped_column(String(32), default=EncounterState.registered, index=True)
    emergency: Mapped[bool] = mapped_column(default=False)
    chief_complaint: Mapped[str | None] = mapped_column(Text)
    disposition: Mapped[str | None] = mapped_column(String(24))  # discharged | admitted | transferred | left
    disposition_note: Mapped[str | None] = mapped_column(Text)
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    completed_at: Mapped[datetime | None]


class EncounterEvent(IdMixin, Base):
    """Timeline: every handoff with time and staff member."""

    __tablename__ = "encounter_events"

    encounter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"), index=True)
    at: Mapped[datetime] = mapped_column(default=utcnow)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(32))  # state | vitals | note | order | result | verify | correction
    from_state: Mapped[str | None] = mapped_column(String(32))
    to_state: Mapped[str | None] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(String(300))
    details: Mapped[dict | None] = mapped_column(JSON)


class ClinicalNote(IdMixin, TimestampMixin, Base):
    """Doctor's note. Draft until signed; a signed note is never edited — amendments supersede it."""

    __tablename__ = "clinical_notes"

    encounter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(12), default="draft")  # draft | signed
    version: Mapped[int] = mapped_column(default=1)
    body: Mapped[str] = mapped_column(Text)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinical_notes.id"))
    signed_at: Mapped[datetime | None]


class InvestigationOrder(IdMixin, TimestampMixin, Base):
    __tablename__ = "investigation_orders"

    encounter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    ordered_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String(12))  # lab | radiology
    test_code: Mapped[str] = mapped_column(String(48))
    test_name: Mapped[str] = mapped_column(String(120))
    priority: Mapped[str] = mapped_column(String(12), default="routine")  # routine | urgent
    clinical_note: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(12), default="ordered", index=True)  # ordered|resulted|verified|cancelled


class LabResult(IdMixin, Base):
    __tablename__ = "lab_results"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigation_orders.id", ondelete="CASCADE"),
                                                unique=True)
    result_text: Mapped[str] = mapped_column(Text)
    abnormal: Mapped[bool] = mapped_column(default=False)
    entered_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    entered_at: Mapped[datetime] = mapped_column(default=utcnow)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime | None]
