import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.triage import Tap, TriageOut

VitalKind = Literal["systolic_bp", "diastolic_bp", "pulse", "temp_c", "spo2", "resp_rate", "weight_kg"]

# Plausible measurement ranges (input validation only, NOT clinical thresholds — those live in red_flags.json).
VITAL_RANGES: dict[str, tuple[float, float, str]] = {
    "systolic_bp": (50, 260, "mmHg"),
    "diastolic_bp": (30, 160, "mmHg"),
    "pulse": (20, 250, "bpm"),
    "temp_c": (30, 45, "°C"),
    "spo2": (50, 100, "%"),
    "resp_rate": (4, 80, "/min"),
    "weight_kg": (0.5, 300, "kg"),
}


class WorkerTriageIn(BaseModel):
    taps: list[Tap] = Field(default_factory=list, max_length=20)
    family_phone: str | None = Field(default=None, max_length=20, pattern=r"^\+?[0-9 ]{7,20}$")


class WorkerTriageStartOut(BaseModel):
    """Recovery code is returned once, for the slip handed to the family. No device key: the worker never holds it."""

    triage: TriageOut
    patient_id: uuid.UUID
    vitalis_id: str
    recovery_code: str


class VitalIn(BaseModel):
    kind: VitalKind
    value: float
    measured_at: datetime | None = None


class VitalsIn(BaseModel):
    report_id: uuid.UUID
    readings: list[VitalIn] = Field(min_length=1, max_length=10)


class WorkerReferralOut(BaseModel):
    id: uuid.UUID
    report_id: uuid.UUID
    status: str
    vitalis_id: str
    facility_id: uuid.UUID
    facility_name: str
    facility_phone: str | None
    facility_lat: float
    facility_lng: float
    care_type: str | None
    care_label: str | None
    red_flag: bool
    red_flag_message: str | None
    distance_km: float | None
    eta_minutes: int | None
    decision_reason: str | None
    next_referral_id: uuid.UUID | None
    previous_facility_name: str | None
    directions_url: str
    created_at: datetime
    accepted_at: datetime | None
    declined_at: datetime | None
    arrived_at: datetime | None
    overdue_at: datetime | None
