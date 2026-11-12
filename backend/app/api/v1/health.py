from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import Envelope, ok

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    database: str
    version: str


@router.get("/health", response_model=Envelope[Health])
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("select 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001 - health reports, never raises
        db_status = "down"
    return ok(
        Health(status="ok" if db_status == "ok" else "degraded", database=db_status, version="0.1.0")
    )
