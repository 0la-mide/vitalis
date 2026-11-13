import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import WorkerType

StaffRole = Literal["receptionist", "nurse", "doctor", "lab", "radiology"]


class StaffRegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    phone: str | None = Field(default=None, max_length=20, pattern=r"^\+?[0-9 ]{7,20}$")
    facility_id: uuid.UUID
    role: StaffRole
    licence_number: str = Field(min_length=3, max_length=64)


class RegisteredOut(BaseModel):
    user_id: uuid.UUID
    status: str
    facility_id: uuid.UUID | None = None
    message: str


class FacilityOption(BaseModel):
    id: uuid.UUID
    name: str
    lga: str


class UploadOut(BaseModel):
    id: uuid.UUID
    original_name: str
    content_type: str
    size_bytes: int


class VerificationOut(BaseModel):
    id: uuid.UUID
    subject_type: Literal["facility", "worker", "staff"]
    status: str
    created_at: datetime
    decided_at: datetime | None
    reason: str | None
    reviewer_name: str | None
    # subject
    user_id: uuid.UUID | None
    user_name: str | None
    user_email: str | None
    user_role: str | None
    facility_id: uuid.UUID | None
    facility_name: str | None
    facility_lga: str | None
    facility_type: str | None
    details: dict
    documents: list[UploadOut]


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject", "suspend"]
    reason: str | None = Field(default=None, max_length=500)


WORKER_TYPES = [w.value for w in WorkerType]
