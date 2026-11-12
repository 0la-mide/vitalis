import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin, utcnow
from app.models.enums import AlertStatus, ReferralStatus, TriageStatus


class TriageReport(IdMixin, TimestampMixin, Base):
    __tablename__ = "triage_reports"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    worker_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    entry: Mapped[str | None] = mapped_column(String(32))  # emergency button code or "other"
    status: Mapped[str] = mapped_column(String(16), default=TriageStatus.open)
    # Patient context: age_group, sex, pregnant, who
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    # Accumulated answers: {"symptoms": [{code, region, severity, onset}], "regions": [...]}
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    lga: Mapped[str | None] = mapped_column(String(80))
    action_level: Mapped[str | None] = mapped_column(String(16))
    care_type: Mapped[str | None] = mapped_column(String(32))
    red_flag: Mapped[bool] = mapped_column(default=False)
    red_flag_codes: Mapped[list] = mapped_column(JSON, default=list)
    red_flag_message: Mapped[str | None] = mapped_column(Text)
    rules_version: Mapped[str | None] = mapped_column(String(32))
    heads_up_sent_at: Mapped[datetime | None]


class SymptomTap(IdMixin, Base):
    __tablename__ = "symptom_taps"

    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("triage_reports.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int]
    kind: Mapped[str] = mapped_column(String(24))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ModelPrediction(IdMixin, Base):
    __tablename__ = "model_predictions"

    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("triage_reports.id", ondelete="CASCADE"), index=True
    )
    model_version: Mapped[str] = mapped_column(String(48))
    ok: Mapped[bool]
    latency_ms: Mapped[int]
    error: Mapped[str | None] = mapped_column(String(200))
    input: Mapped[dict] = mapped_column(JSON)
    output: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Vital(IdMixin, Base):
    __tablename__ = "vitals"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    report_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("triage_reports.id", ondelete="SET NULL"))
    encounter_id: Mapped[uuid.UUID | None]  # FK added with encounters (Phase 6)
    source: Mapped[str] = mapped_column(String(16))  # worker | nurse
    kind: Mapped[str] = mapped_column(String(24))  # spo2, systolic_bp, diastolic_bp, pulse, temp_c, resp_rate, weight_kg
    value: Mapped[float]
    unit: Mapped[str] = mapped_column(String(16))
    measured_at: Mapped[datetime]
    entered_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    corrected_from: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vitals.id"))


class Referral(IdMixin, TimestampMixin, Base):
    __tablename__ = "referrals"

    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("triage_reports.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    worker_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    previous_referral_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("referrals.id"))
    status: Mapped[str] = mapped_column(String(16), default=ReferralStatus.pending, index=True)
    rank: Mapped[int] = mapped_column(default=1)
    score: Mapped[float | None]
    distance_km: Mapped[float | None]
    eta_minutes: Mapped[int | None]
    care_type: Mapped[str | None] = mapped_column(String(32))
    heads_up: Mapped[bool] = mapped_column(default=False)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    accepted_at: Mapped[datetime | None]
    declined_at: Mapped[datetime | None]
    more_info_at: Mapped[datetime | None]
    cancelled_at: Mapped[datetime | None]
    arrived_at: Mapped[datetime | None]
    overdue_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]


class FacilityAlert(IdMixin, TimestampMixin, Base):
    """Heads-up sent to top facilities when a red flag fires."""

    __tablename__ = "facility_alerts"

    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("triage_reports.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default=AlertStatus.sent)
    care_type: Mapped[str | None] = mapped_column(String(32))
    message: Mapped[str | None] = mapped_column(Text)
    ready_at: Mapped[datetime | None]
    ready_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
