import uuid
from datetime import date, datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, IdMixin, TimestampMixin, utcnow
from app.models.enums import Role, VerificationStatus


class User(IdMixin, TimestampMixin, Base):
    """Staff, frontline workers and admins. Patients are NOT users."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[str] = mapped_column(String(32), default=Role.worker)
    status: Mapped[str] = mapped_column(String(16), default=VerificationStatus.pending, index=True)
    status_reason: Mapped[str | None] = mapped_column(Text)
    licence_number: Mapped[str | None] = mapped_column(String(64))
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("facilities.id", ondelete="SET NULL"), index=True
    )
    last_login_at: Mapped[datetime | None]

    facility = relationship("Facility", lazy="raise")
    worker_profile = relationship("WorkerProfile", uselist=False, lazy="raise", back_populates="user")


class WorkerProfile(IdMixin, Base):
    __tablename__ = "worker_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    worker_type: Mapped[str] = mapped_column(String(32))
    business_name: Mapped[str | None] = mapped_column(String(200))
    lga: Mapped[str | None] = mapped_column(String(80))
    lat: Mapped[float | None]
    lng: Mapped[float | None]

    user = relationship("User", lazy="raise", back_populates="worker_profile")


class Patient(IdMixin, TimestampMixin, Base):
    """No login. Identified by a device key (hashed) and a recovery code (hashed)."""

    __tablename__ = "patients"

    vitalis_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    device_key_hash: Mapped[str] = mapped_column(String(64), index=True)
    recovery_hash: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str | None] = mapped_column(String(32))
    display_name: Mapped[str | None] = mapped_column(String(120))  # synthetic demo label only
    age_group: Mapped[str | None] = mapped_column(String(16))
    sex: Mapped[str | None] = mapped_column(String(8))
    pregnant: Mapped[bool] = mapped_column(default=False)
    date_of_birth: Mapped[date | None]
    created_by_worker_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class AuditEvent(IdMixin, Base):
    __tablename__ = "audit_events"

    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    actor_type: Mapped[str] = mapped_column(String(16))  # user | patient | system
    actor_id: Mapped[uuid.UUID | None]
    action: Mapped[str] = mapped_column(String(64), index=True)
    subject_type: Mapped[str | None] = mapped_column(String(32))
    subject_id: Mapped[uuid.UUID | None]
    facility_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    details: Mapped[dict | None] = mapped_column(JSON)
    request_id: Mapped[str | None] = mapped_column(String(32))


class PushSubscription(IdMixin, TimestampMixin, Base):
    __tablename__ = "push_subscriptions"

    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    p256dh: Mapped[str] = mapped_column(String(255))
    auth: Mapped[str] = mapped_column(String(255))


class PatientHistoryEntry(IdMixin, Base):
    """The patient's record across the network: allergies, conditions, medicines, family history.

    Each entry keeps where it was recorded, so the doctor AI can say "recorded at <hospital>, <date>".
    """

    __tablename__ = "patient_history"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)  # allergy | condition | medication | family
    text: Mapped[str] = mapped_column(String(200))  # e.g. "Sulfonamides (Septrin)", "Hypertension", "Amlodipine 5 mg"
    detail: Mapped[str | None] = mapped_column(String(200))  # reaction / relationship / dose
    onset_age: Mapped[int | None]  # family history
    active: Mapped[bool] = mapped_column(default=True)
    recorded_at: Mapped[datetime] = mapped_column(default=utcnow)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("facilities.id", ondelete="SET NULL"))
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
