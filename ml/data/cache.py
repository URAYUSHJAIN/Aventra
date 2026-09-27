"""Tiny thread-safe in-memory TTL cache (ML Pipeline §40: no Redis until required)."""
from __future__ import annotations

import time
from threading import Lock
from typing import Any, Callable

_store: dict[str, tuple[float, Any]] = {}
_lock = Lock()


def get_or_set(key: str, ttl_seconds: float, factory: Callable[[], Any]) -> Any:
    now = time.monotonic()
    with _lock:
        hit = _store.get(key)
        if hit and hit[0] > now:
            return hit[1]
    value = factory()
    with _lock:
        _store[key] = (now + ttl_seconds, value)
    return value


def invalidate(prefix: str = "") -> None:
    with _lock:
        for key in [key for key in _store if key.startswith(prefix)]:
            del _store[key]
