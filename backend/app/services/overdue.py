import asyncio
import logging

from app.core.config import get_settings
from app.core.db import sessionmaker
from app.services.referrals import run_overdue_check

log = logging.getLogger("vitalis.overdue")


async def _loop() -> None:
    interval = get_settings().overdue_check_seconds
    while True:
        try:
            async with sessionmaker()() as db:
                n = await run_overdue_check(db)
                if n:
                    log.info("overdue referrals marked", extra={"fields": {"count": n}})
        except Exception:
            log.exception("overdue check failed")
        await asyncio.sleep(interval)


def start_overdue_loop() -> asyncio.Task:
    return asyncio.create_task(_loop())
