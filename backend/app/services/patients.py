import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import new_secret, sha256_hex
from app.models import Patient

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I/L


def _chunk(n: int) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


def new_vitalis_id() -> str:
    return f"VT-{_chunk(4)}-{_chunk(2)}"


def new_recovery_code() -> str:
    return f"{_chunk(4)}-{_chunk(4)}-{_chunk(4)}"


def normalise_recovery(code: str) -> str:
    return code.strip().upper().replace(" ", "")


async def create_patient(
    db: AsyncSession,
    *,
    phone: str | None = None,
    age_group: str | None = None,
    sex: str | None = None,
    pregnant: bool = False,
    created_by_worker_id: uuid.UUID | None = None,
    display_name: str | None = None,
    full_name: str | None = None,
) -> tuple[Patient, str, str]:
    """Returns (patient, device_secret, recovery_code). Only hashes are stored."""
    for _ in range(10):
        vid = new_vitalis_id()
        exists = (await db.execute(select(Patient.id).where(Patient.vitalis_id == vid))).first()
        if not exists:
            break
    else:  # pragma: no cover
        raise RuntimeError("Could not allocate VITALIS ID")
    device_secret = new_secret(32)
    recovery = new_recovery_code()
    p = Patient(
        vitalis_id=vid,
        device_key_hash=sha256_hex(device_secret),
        recovery_hash=sha256_hex(normalise_recovery(recovery)),
        phone=phone,
        age_group=age_group,
        sex=sex,
        pregnant=pregnant,
        created_by_worker_id=created_by_worker_id,
        display_name=display_name,
        full_name=(full_name or "").strip() or None,
    )
    db.add(p)
    await db.flush()
    return p, device_secret, recovery


def rotate_keys(p: Patient) -> tuple[str, str]:
    device_secret = new_secret(32)
    recovery = new_recovery_code()
    p.device_key_hash = sha256_hex(device_secret)
    p.recovery_hash = sha256_hex(normalise_recovery(recovery))
    return device_secret, recovery


def apply_identity(p: Patient, full_name: str | None, nhia_number: str | None) -> list[str]:
    """Updates the fields that were sent ("" clears). Returns the names of the changed fields."""
    import re

    from app.core.errors import AppError

    changed = []
    if full_name is not None:
        name = " ".join(full_name.split())
        if name and len(name) < 2:
            raise AppError(422, "validation_error", "Name is too short")
        if (name or None) != p.full_name:
            p.full_name = name or None
            changed.append("full_name")
    if nhia_number is not None:
        num = nhia_number.strip().upper()
        if num and not re.fullmatch(r"[A-Z0-9/ .-]{4,24}", num):
            raise AppError(422, "validation_error", "NHIA number: 4-24 letters, digits, / . or -")
        if (num or None) != p.nhia_number:
            p.nhia_number = num or None
            changed.append("nhia_number")
    return changed
