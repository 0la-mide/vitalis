"""Verification document storage: PDF/JPG/PNG only, max 5 MB, magic bytes checked, random names, private dir."""

import hashlib
import secrets
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import Upload

MAX_BYTES = 5 * 1024 * 1024
# magic prefix -> (content type, extension)
MAGIC: list[tuple[bytes, str, str]] = [
    (b"%PDF-", "application/pdf", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
]


def sniff(head: bytes) -> tuple[str, str] | None:
    for magic, ctype, ext in MAGIC:
        if head.startswith(magic):
            return ctype, ext
    return None


def upload_dir() -> Path:
    d = Path(get_settings().upload_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d


async def read_limited(file: UploadFile) -> bytes:
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise AppError(413, "file_too_large", "Document must be 5 MB or smaller")
    if not data:
        raise AppError(422, "file_empty", "Document is empty")
    return data


def store_bytes(
    data: bytes, original_name: str, kind: str, owner_user_id: uuid.UUID | None, facility_id: uuid.UUID | None
) -> Upload:
    sniffed = sniff(data[:16])
    if not sniffed:
        raise AppError(415, "file_type", "Only PDF, JPG or PNG documents are accepted")
    ctype, ext = sniffed
    stored = f"{secrets.token_hex(16)}.{ext}"
    (upload_dir() / stored).write_bytes(data)
    return Upload(
        owner_user_id=owner_user_id,
        facility_id=facility_id,
        kind=kind,
        original_name=Path(original_name or "document").name[:200],
        stored_name=stored,
        content_type=ctype,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


async def save_upload(
    db: AsyncSession,
    file: UploadFile,
    kind: str,
    owner_user_id: uuid.UUID | None = None,
    facility_id: uuid.UUID | None = None,
) -> Upload:
    data = await read_limited(file)
    up = store_bytes(data, file.filename or "document", kind, owner_user_id, facility_id)
    db.add(up)
    await db.flush()
    return up


def path_for(up: Upload) -> Path:
    p = (upload_dir() / up.stored_name).resolve()
    if p.parent != upload_dir().resolve():  # defence in depth against path tricks
        raise AppError(404, "not_found", "Not found")
    return p
