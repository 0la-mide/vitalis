import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class FacilityBrief(BaseModel):
    id: uuid.UUID
    name: str
    status: str


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    status: str
    status_reason: str | None
    facility: FacilityBrief | None
    csrf_token: str | None = None
