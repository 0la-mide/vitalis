from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import get_settings


def _ip_and_patient_key(request: Request) -> str:
    # Device key is hashed into the bucket name so the raw secret never sits in memory keys.
    import hashlib

    key = request.headers.get("x-patient-key", "")
    suffix = hashlib.sha256(key.encode()).hexdigest()[:12] if key else "anon"
    return f"{get_remote_address(request)}:{suffix}"


limiter = Limiter(
    key_func=get_remote_address,
    enabled=get_settings().rate_limit_enabled,
    headers_enabled=False,
)
patient_key = _ip_and_patient_key
