"""In-process pub/sub for Server-Sent Events.

Channels: "referral:<id>", "facility:<id>", "report:<id>", "worker:<id>".
Single backend process for the MVP. For several workers, swap this for Postgres LISTEN/NOTIFY.
"""

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

from fastapi.encoders import jsonable_encoder

# no-transform stops proxies (Next dev server, CDNs) from gzipping and buffering the stream.
SSE_HEADERS = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"}


class Broker:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)

    def publish(self, channel: str, event: str, data: Any) -> None:
        payload = json.dumps(jsonable_encoder(data))
        for q in list(self._subs.get(channel, ())):
            try:
                q.put_nowait((event, payload))
            except asyncio.QueueFull:
                pass

    async def subscribe(self, *channels: str, heartbeat: float = 15.0) -> AsyncIterator[dict]:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        for ch in channels:
            self._subs[ch].add(q)
        try:
            yield {"event": "ready", "data": "{}"}
            while True:
                try:
                    event, payload = await asyncio.wait_for(q.get(), timeout=heartbeat)
                    yield {"event": event, "data": payload}
                except TimeoutError:
                    yield {"event": "ping", "data": "{}"}
        finally:
            for ch in channels:
                self._subs[ch].discard(q)
                if not self._subs[ch]:
                    self._subs.pop(ch, None)

    def subscriber_count(self, channel: str) -> int:
        return len(self._subs.get(channel, ()))


broker = Broker()
