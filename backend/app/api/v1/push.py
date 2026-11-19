"""Web Push sign-up: the patient's phone (device key) or a signed-in staff/worker browser."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import check_csrf, current_patient, current_user
from app.core.errors import Envelope, ok
from app.core.ratelimit import limiter, patient_key
from app.models import Patient, PushSubscription, User
from app.services import push

router = APIRouter(tags=["push"])


class PushKeys(BaseModel):
    p256dh: str = Field(max_length=255)
    auth: str = Field(max_length=255)


class SubscriptionIn(BaseModel):
    endpoint: str = Field(max_length=2000, pattern=r"^https://")
    keys: PushKeys


class EndpointIn(BaseModel):
    endpoint: str = Field(max_length=2000)


class PushKey(BaseModel):
    public_key: str


@router.get("/push/key", response_model=Envelope[PushKey])
async def key():
    return ok(PushKey(public_key=push.vapid_keys()[0]))


@router.post("/me/push", response_model=Envelope[dict])
async def patient_subscribe(request: Request, body: SubscriptionIn, patient: Patient = Depends(current_patient),
                            db: AsyncSession = Depends(get_db)):
    await push.subscribe(db, endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth,
                         patient_id=patient.id, user_agent=request.headers.get("user-agent"))
    return ok({"subscribed": True})


@router.post("/push/subscribe", response_model=Envelope[dict])
async def staff_subscribe(request: Request, body: SubscriptionIn, user: User = Depends(current_user),
                          db: AsyncSession = Depends(get_db)):
    await push.subscribe(db, endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth, user_id=user.id,
                         user_agent=request.headers.get("user-agent"))
    return ok({"subscribed": True})


@router.post("/push/unsubscribe", response_model=Envelope[dict])
async def unsubscribe(body: EndpointIn, db: AsyncSession = Depends(get_db)):
    """Knowing the (secret, browser-issued) endpoint is enough to stop alerts to that browser."""
    await db.execute(delete(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    await db.commit()
    return ok({"subscribed": False})


# ---------- test alert: "is this phone really getting alerts?" ----------
class TestOut(BaseModel):
    devices: int


async def _test(db: AsyncSession, *, patient_id=None, user_id=None) -> int:
    col = PushSubscription.patient_id if patient_id else PushSubscription.user_id
    n = int((await db.execute(select(func.count()).select_from(PushSubscription).where(col == (patient_id or user_id)))).scalar_one())
    if n:
        await push.notify(db, title="VITALIS test alert", body="Alerts are working on this phone.", url="/",
                          patient_ids=[patient_id] if patient_id else None, user_ids=[user_id] if user_id else None,
                          tag="vitalis-test")
    return n


@router.post("/me/push/test", response_model=Envelope[TestOut])
@limiter.limit("5/minute", key_func=patient_key)
async def patient_test(request: Request, patient: Patient = Depends(current_patient), db: AsyncSession = Depends(get_db)):
    return ok(TestOut(devices=await _test(db, patient_id=patient.id)))


@router.post("/push/test", response_model=Envelope[TestOut])
@limiter.limit("5/minute")
async def staff_test(request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    check_csrf(request)
    return ok(TestOut(devices=await _test(db, user_id=user.id)))
