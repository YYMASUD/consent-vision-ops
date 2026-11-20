"""In-process pub/sub event bus with WebSocket fan-out."""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

_subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
_handlers: dict[str, list[Callable[[dict], Awaitable[None]]]] = defaultdict(list)
_recent: deque[tuple[datetime, str, dict]] = deque(maxlen=500)


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def publish(event_type: str, payload: dict[str, Any], *, topic: str = "live") -> None:
    """Publish an event to all topic subscribers and async handlers."""
    event = {"type": event_type, "topic": topic, "ts": _now(), "data": payload}
    _recent.append((datetime.now(UTC), topic, event))
    for q in list(_subscribers[topic]):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            # bounded queues: drop rather than block the pipeline
            pass
    for handler in list(_handlers[topic]):
        try:
            await handler(event)
        except Exception:  # pragma: no cover - handler isolation
            pass


def subscribe(topic: str = "live") -> asyncio.Queue:
    """Subscribe a bounded queue for a topic."""
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _subscribers[topic].add(q)
    return q


def unsubscribe(topic: str, q: asyncio.Queue) -> None:
    """Remove a subscriber queue."""
    _subscribers[topic].discard(q)


def on(topic: str, handler: Callable[[dict], Awaitable[None]]) -> None:
    """Register an async handler for a topic."""
    _handlers[topic].append(handler)


async def stream(topic: str = "live") -> AsyncIterator[dict]:
    """Async generator yielding events for WebSocket streaming (with keepalive pings)."""
    q = subscribe(topic)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=15.0)
                yield event
            except TimeoutError:
                yield {"type": "ping", "ts": _now()}
    finally:
        unsubscribe(topic, q)


def recent_events(topic: str = "live", limit: int = 50) -> list[dict]:
    """Recent events for dashboard catch-up."""
    evts = [e for _ts, t, e in _recent if t == topic]
    return evts[-limit:]


def snapshot() -> dict:
    """Debug/state snapshot."""
    return {
        "topics": {k: len(v) for k, v in _subscribers.items()},
        "recent_count": len(_recent),
    }

