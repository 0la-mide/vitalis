"""Web Push sign-up: the patient's phone (device key) or a signed-in staff/worker browser."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import current_patient, current_user
from app.core.errors import Envelope, ok
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
async def patient_subscribe(body: SubscriptionIn, patient: Patient = Depends(current_patient),
                            db: AsyncSession = Depends(get_db)):
    await push.subscribe(db, endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth,
                         patient_id=patient.id)
    return ok({"subscribed": True})


@router.post("/push/subscribe", response_model=Envelope[dict])
async def staff_subscribe(body: SubscriptionIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await push.subscribe(db, endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth, user_id=user.id)
    return ok({"subscribed": True})


@router.post("/push/unsubscribe", response_model=Envelope[dict])
async def unsubscribe(body: EndpointIn, db: AsyncSession = Depends(get_db)):
    """Knowing the (secret, browser-issued) endpoint is enough to stop alerts to that browser."""
    await db.execute(delete(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    await db.commit()
    return ok({"subscribed": False})
