from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from threading import RLock
from typing import Any, AsyncIterator

from fastapi import Request
from sse_starlette.sse import EventSourceResponse


@dataclass(frozen=True, slots=True)
class DashboardEvent:
    id: int
    event: str
    data: dict[str, Any]
    created_at: datetime

    def as_sse(self) -> dict[str, str]:
        return {
            "id": str(self.id),
            "event": self.event,
            "data": json.dumps(self.data, separators=(",", ":"), default=str),
        }


@dataclass(frozen=True, slots=True)
class _Subscriber:
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[DashboardEvent]


class DashboardBroadcaster:
    """Thread-safe fan-out with a bounded replay window.

    Event ingestion and decision persistence run in worker threads while SSE
    consumers live on the ASGI event loop. Each publication therefore enters
    subscriber queues through ``call_soon_threadsafe``.
    """

    def __init__(self, *, replay_size: int = 100) -> None:
        self._events: deque[DashboardEvent] = deque(maxlen=replay_size)
        self._subscribers: dict[int, _Subscriber] = {}
        self._next_event_id = 1
        self._next_subscriber_id = 1
        self._lock = RLock()

    @staticmethod
    def _offer(queue: asyncio.Queue[DashboardEvent], event: DashboardEvent) -> None:
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        queue.put_nowait(event)

    def publish(self, event: str, data: dict[str, Any]) -> DashboardEvent:
        with self._lock:
            item = DashboardEvent(
                id=self._next_event_id,
                event=event,
                data=dict(data),
                created_at=datetime.now(timezone.utc),
            )
            self._next_event_id += 1
            self._events.append(item)
            subscribers = tuple(self._subscribers.values())
        for subscriber in subscribers:
            subscriber.loop.call_soon_threadsafe(
                self._offer, subscriber.queue, item
            )
        return item

    async def subscribe(
        self,
        request: Request,
        *,
        last_event_id: str | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[DashboardEvent] = asyncio.Queue(maxsize=100)
        try:
            replay_after = int(last_event_id) if last_event_id is not None else None
        except ValueError:
            replay_after = None
        with self._lock:
            subscriber_id = self._next_subscriber_id
            self._next_subscriber_id += 1
            replay = (
                tuple(item for item in self._events if item.id > replay_after)
                if replay_after is not None
                else ()
            )
            self._subscribers[subscriber_id] = _Subscriber(loop, queue)
        try:
            for item in replay:
                yield item.as_sse()
            while not await request.is_disconnected():
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=1.0)
                except TimeoutError:
                    continue
                yield item.as_sse()
        finally:
            with self._lock:
                self._subscribers.pop(subscriber_id, None)

    def reset(self) -> None:
        """Clear process-local state; intended for isolated tests."""
        with self._lock:
            self._events.clear()
            self._subscribers.clear()
            self._next_event_id = 1
            self._next_subscriber_id = 1

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)


broadcaster = DashboardBroadcaster()


def stream_response(request: Request) -> EventSourceResponse:
    return EventSourceResponse(
        broadcaster.subscribe(
            request,
            last_event_id=request.headers.get("last-event-id"),
        ),
        ping=15,
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
