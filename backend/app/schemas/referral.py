import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ReferralCreateIn(BaseModel):
    facility_id: uuid.UUID | None = None


class FacilityPublic(BaseModel):
    id: uuid.UUID
    name: str
    lga: str
    address: str | None
    phone: str | None
    lat: float
    lng: float


class ReferralPatientOut(BaseModel):
    """What the family sees. No clinical labels."""

    id: uuid.UUID
    report_id: uuid.UUID
    status: str
    facility: FacilityPublic
    distance_km: float | None
    eta_minutes: int | None
    eta_is_estimate: bool = True
    directions_url: str
    what_to_bring: list[str]
    vitalis_id: str
    decline_reason: str | None
    next_referral_id: uuid.UUID | None
    previous_facility_name: str | None
    created_at: datetime
    accepted_at: datetime | None
    arrived_at: datetime | None
    overdue_at: datetime | None


class DecisionIn(BaseModel):
    action: Literal["accept", "decline", "more_info"]
    reason: str | None = Field(default=None, max_length=500)


class SymptomLine(BaseModel):
    code: str
    label: str
    region: str | None
    severity: int | None
    onset: str | None


class VitalLine(BaseModel):
    kind: str
    value: float
    unit: str
    source: str
    measured_at: datetime


class IncomingPatient(BaseModel):
    vitalis_id: str
    age_group: str | None
    sex: str | None
    pregnant: bool


class IncomingItem(BaseModel):
    kind: Literal["referral", "alert"]
    id: uuid.UUID
    report_id: uuid.UUID
    status: str
    created_at: datetime
    patient: IncomingPatient
    care_type: str | None
    red_flag: bool
    red_flag_message: str | None
    symptoms: list[SymptomLine]
    vitals: list[VitalLine]
    distance_km: float | None
    eta_minutes: int | None
    expected_arrival_at: datetime | None
    decision_reason: str | None
    referred_by: str | None
    accepted_at: datetime | None
    arrived_at: datetime | None
    overdue_at: datetime | None


class DecisionOut(BaseModel):
    referral_id: uuid.UUID
    status: str
    next_referral_id: uuid.UUID | None
