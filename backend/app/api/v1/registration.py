"""Self-registration. Everything starts `pending`; nobody sees patient data until verified."""

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.db import get_db
from app.core.deps import current_user_any_status
from app.core.errors import AppError, Envelope, ok
from app.core.ratelimit import limiter
from app.core.security import hash_password
from app.engines.triage.data import care_types
from app.models import Facility, FacilityService, User, Verification, WorkerProfile
from app.models.enums import Availability, Role, VerificationStatus
from app.schemas.registration import FacilityOption, RegisteredOut, StaffRegisterIn
from app.services.triage import lgas
from app.services.uploads import save_upload
from app.services.verification import latest_for_user

router = APIRouter(prefix="/auth", tags=["registration"])

FacilityType = Literal["teaching", "general", "specialist", "clinic", "phc"]
WorkerKind = Literal["chemist", "pharmacist", "chew", "midwife"]
_email = TypeAdapter(EmailStr)


def lga_names() -> list[str]:
    return [row["name"] for row in lgas()["lgas"]]


def _check_email(email: str) -> str:
    try:
        return _email.validate_python(email.strip()).lower()
    except ValidationError as exc:
        raise AppError(422, "validation_error", "Invalid email") from exc


def _check_password(pw: str) -> str:
    if len(pw) < 10 or len(pw) > 200:
        raise AppError(422, "weak_password", "Password must be at least 10 characters")
    return pw


def _check_text(value: str, name: str, lo: int = 2, hi: int = 200) -> str:
    v = value.strip()
    if not lo <= len(v) <= hi:
        raise AppError(422, "validation_error", f"{name} must be {lo}-{hi} characters")
    return v


def _check_lga(lga: str) -> str:
    if lga not in lga_names():
        raise AppError(422, "validation_error", "Choose an LGA from the list")
    return lga


async def _email_free(db: AsyncSession, email: str) -> None:
    taken = (await db.execute(select(User.id).where(func.lower(User.email) == email))).first()
    if taken:
        raise AppError(409, "email_taken", "An account with this email already exists")


@router.get("/register/facilities", response_model=Envelope[list[FacilityOption]])
async def facilities_for_registration(db: AsyncSession = Depends(get_db)):
    """Verified facilities that staff can register under."""
    rows = (
        await db.execute(
            select(Facility).where(Facility.status == VerificationStatus.approved).order_by(Facility.name)
        )
    ).scalars()
    return ok([FacilityOption(id=f.id, name=f.name, lga=f.lga) for f in rows])


@router.get("/register/options", response_model=Envelope[dict])
async def registration_options():
    return ok(
        {
            "lgas": lga_names(),
            "services": [{"code": s["code"], "name": s["name"]} for s in care_types()["services"]],
            "facility_types": ["teaching", "general", "specialist", "clinic", "phc"],
            "worker_types": ["chemist", "pharmacist", "chew", "midwife"],
            "staff_roles": ["receptionist", "nurse", "doctor", "lab"],
        }
    )


@router.post("/register/facility", response_model=Envelope[RegisteredOut])
@limiter.limit("5/hour")
async def register_facility(
    request: Request,
    facility_name: str = Form(...),
    facility_type: FacilityType = Form(...),
    lga: str = Form(...),
    address: str = Form(...),
    facility_phone: str = Form(...),
    lat: float = Form(..., ge=-90, le=90),
    lng: float = Form(..., ge=-180, le=180),
    facility_licence_number: str = Form(...),
    services: str = Form(""),
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str | None = Form(None),
    document: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    email = _check_email(email)
    await _email_free(db, email)
    valid_codes = {s["code"] for s in care_types()["services"]}
    codes = [c for c in {c.strip() for c in services.split(",")} if c]
    if any(c not in valid_codes for c in codes):
        raise AppError(422, "validation_error", "Unknown service")

    fac = Facility(
        name=_check_text(facility_name, "Facility name"),
        type=facility_type,
        lga=_check_lga(lga),
        address=_check_text(address, "Address", 3, 300),
        phone=_check_text(facility_phone, "Phone", 7, 20),
        lat=lat,
        lng=lng,
        licence_number=_check_text(facility_licence_number, "Licence number", 3, 64),
        status=VerificationStatus.pending,
    )
    db.add(fac)
    await db.flush()
    for c in codes:
        db.add(FacilityService(facility_id=fac.id, service_code=c, availability_status=Availability.unknown))
    admin = User(
        email=email,
        password_hash=hash_password(_check_password(password)),
        full_name=_check_text(full_name, "Full name"),
        phone=phone,
        role=Role.facility_admin,
        status=VerificationStatus.pending,
        facility_id=fac.id,
    )
    db.add(admin)
    await db.flush()
    up = await save_upload(db, document, "facility_licence", admin.id, fac.id)
    v = Verification(
        subject_type="facility",
        subject_user_id=admin.id,
        subject_facility_id=fac.id,
        documents=[str(up.id)],
        details={"licence_number": fac.licence_number, "services": codes},
    )
    db.add(v)
    await audit(db, "register.facility", actor_id=admin.id, subject_type="facility", subject_id=fac.id,
                facility_id=fac.id)
    await db.commit()
    return ok(RegisteredOut(user_id=admin.id, facility_id=fac.id, status="pending",
                            message="Submitted. The VITALIS network admin will review your facility."))


@router.post("/register/staff", response_model=Envelope[RegisteredOut])
@limiter.limit("10/hour")
async def register_staff(request: Request, body: StaffRegisterIn, db: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    await _email_free(db, email)
    fac = await db.get(Facility, body.facility_id)
    if not fac or fac.status != VerificationStatus.approved:
        raise AppError(422, "facility_not_verified", "Choose a verified facility")
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        phone=body.phone,
        role=body.role,
        status=VerificationStatus.pending,
        facility_id=fac.id,
        licence_number=body.licence_number.strip(),
    )
    db.add(user)
    await db.flush()
    db.add(Verification(subject_type="staff", subject_user_id=user.id, subject_facility_id=fac.id,
                        details={"licence_number": user.licence_number, "role": body.role}))
    await audit(db, "register.staff", actor_id=user.id, subject_type="staff", subject_id=user.id, facility_id=fac.id)
    await db.commit()
    return ok(RegisteredOut(user_id=user.id, facility_id=fac.id, status="pending",
                            message=f"Submitted. The admin at {fac.name} will review your account."))


@router.post("/register/worker", response_model=Envelope[RegisteredOut])
@limiter.limit("5/hour")
async def register_worker(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str | None = Form(None),
    worker_type: WorkerKind = Form(...),
    licence_number: str = Form(...),
    business_name: str | None = Form(None),
    lga: str = Form(...),
    lat: float | None = Form(None, ge=-90, le=90),
    lng: float | None = Form(None, ge=-180, le=180),
    document: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    email = _check_email(email)
    await _email_free(db, email)
    user = User(
        email=email,
        password_hash=hash_password(_check_password(password)),
        full_name=_check_text(full_name, "Full name"),
        phone=phone,
        role=Role.worker,
        status=VerificationStatus.pending,
        licence_number=_check_text(licence_number, "Licence number", 3, 64),
    )
    db.add(user)
    await db.flush()
    db.add(WorkerProfile(user_id=user.id, worker_type=worker_type, business_name=business_name,
                         lga=_check_lga(lga), lat=lat, lng=lng))
    up = await save_upload(db, document, "worker_licence", user.id, None)
    db.add(Verification(subject_type="worker", subject_user_id=user.id, documents=[str(up.id)],
                        details={"licence_number": user.licence_number, "worker_type": worker_type,
                                 "business_name": business_name, "lga": lga}))
    await audit(db, "register.worker", actor_id=user.id, subject_type="worker", subject_id=user.id)
    await db.commit()
    return ok(RegisteredOut(user_id=user.id, status="pending",
                            message="Submitted. The VITALIS network admin will review your licence."))


@router.post("/resubmit", response_model=Envelope[RegisteredOut])
@limiter.limit("10/hour")
async def resubmit(
    request: Request,
    licence_number: str | None = Form(None),
    document: UploadFile | None = File(None),
    user: User = Depends(current_user_any_status),
    db: AsyncSession = Depends(get_db),
):
    """A rejected applicant corrects their details and goes back into the queue."""
    if user.status != VerificationStatus.rejected:
        raise AppError(409, "not_rejected", "Only rejected registrations can be resubmitted")
    last = await latest_for_user(db, user.id)
    if not last:
        raise AppError(404, "not_found", "No registration found")
    if last.subject_type in ("facility", "worker") and document is None:
        raise AppError(422, "document_required", "Upload a corrected document")
    docs = list(last.documents or [])
    if document is not None:
        up = await save_upload(db, document, f"{last.subject_type}_licence", user.id, last.subject_facility_id)
        docs = [str(up.id)]
    details = dict(last.details or {})
    if licence_number:
        lic = _check_text(licence_number, "Licence number", 3, 64)
        details["licence_number"] = lic
        if last.subject_type == "facility":
            fac = await db.get(Facility, last.subject_facility_id)
            if fac:
                fac.licence_number = lic
        else:
            user.licence_number = lic
    db.add(Verification(subject_type=last.subject_type, subject_user_id=user.id,
                        subject_facility_id=last.subject_facility_id, documents=docs,
                        details={**details, "resubmission_of": str(last.id)}))
    user.status = VerificationStatus.pending
    user.status_reason = None
    if last.subject_type == "facility":
        fac = await db.get(Facility, last.subject_facility_id)
        if fac:
            fac.status = VerificationStatus.pending
            fac.status_reason = None
    await audit(db, "register.resubmit", actor_id=user.id, subject_type=last.subject_type, subject_id=user.id,
                facility_id=last.subject_facility_id)
    await db.commit()
    return ok(RegisteredOut(user_id=user.id, facility_id=last.subject_facility_id, status="pending",
                            message="Resubmitted for review."))
