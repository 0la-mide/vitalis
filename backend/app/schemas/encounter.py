import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.referral import IncomingPatient, SymptomLine
from app.schemas.worker import VitalIn


class EncounterListItem(BaseModel):
    id: uuid.UUID
    state: str
    state_label: str
    emergency: bool
    patient: IncomingPatient
    care_label: str | None
    headline: str | None  # red-flag message or chief complaint
    created_at: datetime
    updated_at: datetime
    open_orders: int


class ReferralSummary(BaseModel):
    referral_id: uuid.UUID
    referred_by: str | None
    red_flag_message: str | None
    care_type: str | None
    care_label: str | None
    symptoms: list[SymptomLine]
    sent_at: datetime
    arrived_at: datetime | None


class VitalRow(BaseModel):
    id: uuid.UUID
    kind: str
    value: float
    unit: str
    source: str
    measured_at: datetime
    entered_by: str | None
    corrected_from: uuid.UUID | None
    superseded: bool
    urgent: bool


class NoteRow(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID
    author: str
    status: str
    version: int
    body: str
    supersedes_id: uuid.UUID | None
    created_at: datetime
    signed_at: datetime | None


class OrderRow(BaseModel):
    id: uuid.UUID
    category: str
    test_code: str
    test_name: str
    priority: str
    clinical_note: str | None
    status: str
    ordered_by: str | None
    created_at: datetime
    collected_by: str | None = None
    collected_at: datetime | None = None
    result_text: str | None = None
    values: dict | None = None
    abnormal: bool | None = None
    entered_by: str | None = None
    entered_at: datetime | None = None
    verified_by: str | None = None
    verified_at: datetime | None = None


class TimelineRow(BaseModel):
    at: datetime
    actor: str | None
    actor_role: str | None
    kind: str
    summary: str


class Allowed(BaseModel):
    transitions: list[str]
    record_vitals: bool
    write_notes: bool
    order_tests: bool
    cancel: bool


class EncounterOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    state: str
    state_label: str
    emergency: bool
    chief_complaint: str | None
    disposition: str | None
    disposition_note: str | None
    cancel_reason: str | None
    created_at: datetime
    completed_at: datetime | None
    patient: IncomingPatient
    referral: ReferralSummary | None
    vitals: list[VitalRow]
    notes: list[NoteRow]
    orders: list[OrderRow]
    timeline: list[TimelineRow]
    allowed: Allowed


class WalkInIn(BaseModel):
    age_group: Literal["under5", "child", "teen", "adult", "elderly"]
    sex: Literal["female", "male", "unknown"] = "unknown"
    pregnant: bool = False
    emergency: bool = False
    chief_complaint: str = Field(min_length=2, max_length=500)
    family_phone: str | None = Field(default=None, max_length=20, pattern=r"^\+?[0-9 ]{7,20}$")


class WalkInOut(BaseModel):
    encounter_id: uuid.UUID
    vitalis_id: str
    recovery_code: str


class TransitionIn(BaseModel):
    to: Literal["awaiting_nursing", "awaiting_doctor", "results_ready", "awaiting_disposition", "completed",
                "cancelled"]
    disposition: Literal["discharged", "admitted", "transferred", "left"] | None = None
    note: str | None = Field(default=None, max_length=1000)
    reason: str | None = Field(default=None, max_length=500)


class EncounterVitalsIn(BaseModel):
    readings: list[VitalIn] = Field(min_length=1, max_length=10)
    corrected_from: uuid.UUID | None = None  # correcting one earlier reading; the original is kept
    correction_reason: str | None = Field(default=None, max_length=300)


class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=20000)
    note_id: uuid.UUID | None = None  # edit own draft, or amend a signed note (creates a new version)


class OrderItemIn(BaseModel):
    test_code: str = Field(max_length=48)
    priority: Literal["routine", "urgent"] = "routine"
    note: str | None = Field(default=None, max_length=300)


class OrdersIn(BaseModel):
    items: list[OrderItemIn] = Field(min_length=1, max_length=15)


class ResultValueIn(BaseModel):
    value: float | str
    unit: str | None = Field(default=None, max_length=24)


class ResultIn(BaseModel):
    result_text: str = Field(default="", max_length=5000)
    values: dict[str, ResultValueIn] | None = None  # structured parameters, e.g. {"HbA1c": {"value": 7.4, "unit": "%"}}
    abnormal: bool = False


class LabQueueItem(BaseModel):
    order: OrderRow
    encounter_id: uuid.UUID
    vitalis_id: str
    emergency: bool
    patient: IncomingPatient


class TestParam(BaseModel):
    name: str
    unit: str
    lo: float | None = None
    hi: float | None = None
    choices: list[str] | None = None


class TestOption(BaseModel):
    code: str
    name: str
    category: str
    params: list[TestParam] = []
