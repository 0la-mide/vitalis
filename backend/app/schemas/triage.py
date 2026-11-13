"""Patient-facing schemas. NEVER include disease names or likelihoods here."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PatientStartIn(BaseModel):
    phone: str | None = Field(default=None, max_length=20, pattern=r"^\+?[0-9 ]{7,20}$")


class PatientKeysOut(BaseModel):
    patient_id: uuid.UUID
    vitalis_id: str
    device_key: str
    recovery_code: str


class PatientRecoverIn(BaseModel):
    vitalis_id: str = Field(max_length=16)
    recovery_code: str = Field(max_length=20)


class Tap(BaseModel):
    kind: Literal["emergency", "context", "region", "symptom", "severity", "onset", "location"]
    code: str | None = Field(default=None, max_length=48)
    region: str | None = Field(default=None, max_length=32)
    selected: bool | None = None
    value: int | str | None = None
    age_group: str | None = Field(default=None, max_length=16)
    sex: str | None = Field(default=None, max_length=16)
    pregnant: bool | None = None
    who: str | None = Field(default=None, max_length=16)
    lat: float | None = None
    lng: float | None = None
    lga: str | None = Field(default=None, max_length=80)
    client_ts: datetime | None = None


class TriageStartIn(BaseModel):
    taps: list[Tap] = Field(default_factory=list, max_length=20)


class TapsIn(BaseModel):
    taps: list[Tap] = Field(min_length=1, max_length=20)


class RedFlagOut(BaseModel):
    fired: bool
    message: str | None


class HospitalCard(BaseModel):
    facility_id: uuid.UUID
    name: str
    lga: str
    lat: float
    lng: float
    phone: str | None
    distance_km: float
    eta_minutes: int
    eta_is_estimate: bool = True
    score: float
    freshness: Literal["confirmed", "stale", "unknown"]
    last_confirmed_at: datetime | None
    ready_now: bool
    reasons: list[str]
    warnings: list[str]


class ExcludedCard(BaseModel):
    facility_id: uuid.UUID
    name: str
    distance_km: float
    reasons: list[str]


class HospitalSummary(BaseModel):
    nearby: int
    can_handle: int
    ready_now: int
    top: list[HospitalCard]
    excluded: list[ExcludedCard]
    approximate_location: bool


class TriageOut(BaseModel):
    report_id: uuid.UUID
    status: str
    red_flag: RedFlagOut
    care_type: str | None
    care_label: str | None
    action_level: Literal["go_now", "go_today", "see_chemist", "self_care"] | None
    self_care_return_if: list[str]
    what_to_bring: list[str]
    heads_up_sent: bool
    hospitals: HospitalSummary
    context: dict
    answers: dict
    active_referral_id: uuid.UUID | None = None


# ---------- UI taxonomy (public) ----------
class TaxRegion(BaseModel):
    code: str
    view: str
    labels: dict[str, str]
    labels_female: dict[str, str] | None = None  # e.g. "Chest & breasts" on a woman's body
    audio: str


class TaxSymptom(BaseModel):
    code: str
    regions: list[str]
    icon: str
    labels: dict[str, str]
    audio: str
    pregnant_only: bool = False
    female_only: bool = False
    not_child: bool = False  # e.g. breast symptoms: women and teen girls only
    child_only: bool = False
    not_pregnant: bool = False
    emergency_only: bool = False


class TaxEmergency(BaseModel):
    code: str
    icon: str
    labels: dict[str, str]
    audio: str
    context: dict
    symptoms: list[dict]
    next: Literal["emergency", "body", "who_child"]


class TaxWho(BaseModel):
    code: str
    icon: str | None = None
    labels: dict[str, str]
    audio: str
    context: dict
    sub: list["TaxWho"] | None = None


class TaxSeverity(BaseModel):
    value: int
    labels: dict[str, str]
    audio: str


class TaxOnset(BaseModel):
    code: str
    icon: str
    labels: dict[str, str]
    audio: str


class TaxLga(BaseModel):
    name: str
    lat: float
    lng: float


class Taxonomy(BaseModel):
    version: str
    needs_clinical_review: bool
    languages: list[str]
    regions: list[TaxRegion]
    symptoms: list[TaxSymptom]
    emergencies: list[TaxEmergency]
    who: list[TaxWho]
    severity: list[TaxSeverity]
    onset: list[TaxOnset]
    lgas: list[TaxLga]
