"""Web Push: alerts that reach the phone even when VITALIS is closed.

Keys: VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY from .env, or generated once and kept in var/vapid.json (a persistent
volume on the server), so push works with no setup. Messages are short and never clinical (they show on a lock screen).
Sending happens in the background; subscriptions the browser has dropped (404/410) are removed.
"""

import asyncio
import base64
import json
import logging
import uuid
from functools import lru_cache

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import BACKEND_DIR, get_settings
from app.core.db import sessionmaker
from app.models import PushSubscription, User

log = logging.getLogger("vitalis.push")
KEY_FILE = BACKEND_DIR / "var" / "vapid.json"
_pending: set[asyncio.Task] = set()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


@lru_cache
def vapid_keys() -> tuple[str, str]:
    """(public applicationServerKey, private key), both base64url."""
    s = get_settings()
    if s.vapid_public_key and s.vapid_private_key:
        return s.vapid_public_key, s.vapid_private_key
    if KEY_FILE.exists():
        k = json.loads(KEY_FILE.read_text())
        return k["public"], k["private"]
    key = ec.generate_private_key(ec.SECP256R1())
    private = _b64(key.private_numbers().private_value.to_bytes(32, "big"))
    public = _b64(key.public_key().public_bytes(serialization.Encoding.X962,
                                                serialization.PublicFormat.UncompressedPoint))
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_text(json.dumps({"public": public, "private": private}))
    KEY_FILE.chmod(0o600)
    return public, private


async def subscribe(db: AsyncSession, *, endpoint: str, p256dh: str, auth: str,
                    patient_id: uuid.UUID | None = None, user_id: uuid.UUID | None = None) -> None:
    """One row per browser endpoint; re-subscribing moves it to the current owner."""
    row = (await db.execute(select(PushSubscription).where(PushSubscription.endpoint == endpoint))).scalar_one_or_none()
    if not row:
        row = PushSubscription(endpoint=endpoint, p256dh=p256dh, auth=auth)
        db.add(row)
    row.p256dh, row.auth, row.patient_id, row.user_id = p256dh, auth, patient_id, user_id
    await db.commit()


async def notify(db: AsyncSession, *, title: str, body: str, url: str,
                 patient_ids: list[uuid.UUID] | None = None, user_ids: list[uuid.UUID] | None = None,
                 tag: str | None = None) -> None:
    """Queue a push to every device of these patients/users. Returns at once."""
    conds = []
    if patient_ids:
        conds.append(PushSubscription.patient_id.in_(patient_ids))
    if user_ids:
        conds.append(PushSubscription.user_id.in_(user_ids))
    if not conds:
        return
    subs = (await db.execute(select(PushSubscription).where(or_(*conds)))).scalars().all()
    if not subs:
        return
    payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag})
    targets = [(s.endpoint, s.p256dh, s.auth) for s in subs]
    task = asyncio.create_task(_deliver(targets, payload))
    _pending.add(task)
    task.add_done_callback(_pending.discard)


async def notify_facility(db: AsyncSession, facility_id: uuid.UUID, roles: set[str], **kw) -> None:
    ids = list((await db.execute(select(User.id).where(User.facility_id == facility_id,
                                                        User.role.in_(roles)))).scalars())
    await notify(db, user_ids=ids, **kw)


def _subject() -> str:
    s = get_settings()
    return s.vapid_subject or s.public_base_url


def _send_one(endpoint: str, p256dh: str, auth: str, payload: str) -> int:
    from pywebpush import WebPushException, webpush

    _public, private = vapid_keys()
    try:
        webpush({"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}}, data=payload,
                vapid_private_key=private, vapid_claims={"sub": _subject()}, ttl=3600, timeout=8)
        return 201
    except WebPushException as e:
        return e.response.status_code if e.response is not None else 0


async def _deliver(targets: list[tuple[str, str, str]], payload: str) -> None:
    gone = []
    for endpoint, p256dh, auth in targets:
        try:
            status = await asyncio.to_thread(_send_one, endpoint, p256dh, auth, payload)
        except Exception as e:  # noqa: BLE001 - a push failure must never break anything
            log.warning("push failed", extra={"fields": {"error": str(e)}})
            continue
        if status in (404, 410):
            gone.append(endpoint)
        log.info("push", extra={"fields": {"status": status}})
    if gone:
        async with sessionmaker()() as db:
            await db.execute(delete(PushSubscription).where(PushSubscription.endpoint.in_(gone)))
            await db.commit()
