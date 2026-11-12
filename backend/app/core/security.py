import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

_ph = PasswordHasher()
# Pre-computed hash so login timing is the same whether or not the user exists.
_DUMMY_HASH = _ph.hash("not-a-real-password-vitalis")

ACCESS_COOKIE = "vt_access"
REFRESH_COOKIE = "vt_refresh"
CSRF_COOKIE = "vt_csrf"
CSRF_HEADER = "x-csrf-token"


# ---------- passwords ----------
def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    try:
        return _ph.verify(hashed or _DUMMY_HASH, password) and hashed is not None
    except (VerificationError, InvalidHashError):
        return False


# ---------- opaque secrets (device keys, recovery codes, QR tokens) ----------
def new_secret(nbytes: int = 32) -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(nbytes)).rstrip(b"=").decode()


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def secret_matches(value: str, expected_hash: str) -> bool:
    return hmac.compare_digest(sha256_hex(value), expected_hash)


# ---------- JWT ----------
TokenType = Literal["access", "refresh"]


def create_token(user_id: uuid.UUID, token_type: TokenType, extra: dict | None = None) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    ttl = (
        timedelta(minutes=s.access_token_minutes)
        if token_type == "access"
        else timedelta(days=s.refresh_token_days)
    )
    payload = {
        "sub": str(user_id),
        "typ": token_type,
        "iat": now,
        "exp": now + ttl,
        "jti": uuid.uuid4().hex,
        **(extra or {}),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decode_token(token: str, token_type: TokenType) -> dict | None:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != token_type:
        return None
    return payload
