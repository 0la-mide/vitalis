import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, IdMixin, TimestampMixin
from app.models.enums import Availability, VerificationStatus


class Facility(IdMixin, TimestampMixin, Base):
    __tablename__ = "facilities"

    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(32))  # teaching | general | specialist | clinic | phc
    lga: Mapped[str] = mapped_column(String(80), index=True)
    address: Mapped[str | None] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(32))
    lat: Mapped[float]
    lng: Mapped[float]
    status: Mapped[str] = mapped_column(String(16), default=VerificationStatus.pending, index=True)
    status_reason: Mapped[str | None] = mapped_column(String(300))
    licence_number: Mapped[str | None] = mapped_column(String(64))

    services = relationship(
        "FacilityService", lazy="raise", back_populates="facility", cascade="all, delete-orphan"
    )


class Service(Base):
    """Catalogue of matchable services (obstetrician_on_duty, blood_bank, theatre, ...)."""

    __tablename__ = "services"

    code: Mapped[str] = mapped_column(String(48), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(32))  # staff | resource | unit


class FacilityService(IdMixin, Base):
    __tablename__ = "facility_services"
    __table_args__ = (UniqueConstraint("facility_id", "service_code"),)

    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="CASCADE"), index=True
    )
    service_code: Mapped[str] = mapped_column(ForeignKey("services.code"))
    availability_status: Mapped[str] = mapped_column(String(16), default=Availability.unknown)
    last_confirmed_at: Mapped[datetime | None]
    reported_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    facility = relationship("Facility", lazy="raise", back_populates="services")
