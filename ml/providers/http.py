"""Shared HTTP access for providers: token-bucket rate limiting, retries with exponential backoff (honouring
Retry-After), a per-provider circuit breaker, daily budgets and provider_calls logging (health).

Never hammer providers: a request that would exceed the limit waits (bounded) or fails with RateLimited.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

import requests

from ml.providers.base import MalformedResponse, ProviderUnavailable, RateLimited

logger = logging.getLogger(__name__)
USER_AGENT = "Aventra/0.2 (B.Tech research prototype; contact via repository)"
MAX_WAIT_SECONDS = 20.0
FAILURE_THRESHOLD = 5          # consecutive failures that open the circuit
COOLDOWN_SECONDS = 120.0


class TokenBucket:
    def __init__(self, per_minute: float):
        self.capacity = max(1.0, per_minute / 6)       # allow short bursts of ~10 s worth of calls
        self.rate = per_minute / 60.0
        self.tokens = self.capacity
        self.updated = time.monotonic()
        self.lock = threading.Lock()

    def wait_time(self) -> float:
        with self.lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
            self.updated = now
            if self.tokens >= 1:
                self.tokens -= 1
                return 0.0
            return (1 - self.tokens) / self.rate


class CircuitBreaker:
    def __init__(self):
        self.failures = 0
        self.opened_at: float | None = None
        self.lock = threading.Lock()

    def allow(self) -> bool:
        with self.lock:
            if self.opened_at is None:
                return True
            if time.monotonic() - self.opened_at >= COOLDOWN_SECONDS:   # half-open: let one request through
                self.opened_at = None
                self.failures = FAILURE_THRESHOLD - 1
                return True
            return False

    def record(self, ok: bool) -> None:
        with self.lock:
            if ok:
                self.failures, self.opened_at = 0, None
            else:
                self.failures += 1
                if self.failures >= FAILURE_THRESHOLD and self.opened_at is None:
                    self.opened_at = time.monotonic()

    @property
    def state(self) -> str:
        return "open" if self.opened_at is not None else ("degraded" if self.failures else "closed")


_buckets: dict[str, TokenBucket] = {}
_breakers: dict[str, CircuitBreaker] = {}
_registry_lock = threading.Lock()


def bucket(provider: str, per_minute: float) -> TokenBucket:
    with _registry_lock:
        if provider not in _buckets:
            _buckets[provider] = TokenBucket(per_minute)
        return _buckets[provider]


def breaker(provider: str) -> CircuitBreaker:
    with _registry_lock:
        return _breakers.setdefault(provider, CircuitBreaker())


def reset_state() -> None:
    """Tests only: clear limiter and breaker state."""
    with _registry_lock:
        _buckets.clear()
        _breakers.clear()


def _log_call(provider: str, endpoint: str, status: str, http_status, started: float, error: str | None = None) -> None:
    try:
        from ml.data import store
        store.record_provider_call(provider, endpoint, status, http_status, round((time.perf_counter() - started) * 1000, 1), error)
    except Exception:   # health logging must never break a data request (e.g. DB not migrated yet)
        logger.debug("provider_calls logging failed", exc_info=True)


def calls_today(provider: str) -> int:
    from ml.data import store
    midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        return sum(store.provider_call_stats(provider, midnight).values())
    except Exception:
        return 0


def request(provider: str, endpoint: str, url: str, *, per_minute: float, method: str = "GET", params=None, headers=None, json_body=None,
            timeout: float = 20.0, retries: int = 2, daily_budget: int | None = None) -> requests.Response:
    """Rate-limited, retried request. Returns a 2xx response or raises a typed provider error."""
    circuit = breaker(provider)
    if not circuit.allow():
        raise ProviderUnavailable(f"{provider} is temporarily disabled after repeated failures.", provider, reason="circuit_open")
    if daily_budget is not None and calls_today(provider) >= daily_budget:
        raise ProviderUnavailable(f"{provider} daily request budget ({daily_budget}) is exhausted.", provider, reason="budget_exhausted")
    limiter = bucket(provider, per_minute)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})}
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        wait = limiter.wait_time()
        if wait > MAX_WAIT_SECONDS:
            raise RateLimited(f"{provider} local rate limit reached; retry in {wait:.0f}s.", provider, retry_after=wait)
        if wait:
            time.sleep(wait)
        started = time.perf_counter()
        try:
            response = requests.request(method, url, params=params, headers=headers, json=json_body, timeout=(5.0, timeout))
        except requests.RequestException as error:
            last_error = error
            _log_call(provider, endpoint, "error", None, started, repr(error))
            circuit.record(False)
            time.sleep(min(2 ** attempt, 8))
            continue
        if response.status_code in (429, 418):
            retry_after = float(response.headers.get("Retry-After", "0") or 0)
            _log_call(provider, endpoint, "rate_limited", response.status_code, started)
            if attempt < retries and retry_after <= MAX_WAIT_SECONDS:
                time.sleep(max(retry_after, 2 ** attempt))
                continue
            raise RateLimited(f"{provider} rate limit reached.", provider, retry_after=retry_after or None)
        if response.status_code >= 500:
            _log_call(provider, endpoint, "error", response.status_code, started, response.text[:200])
            circuit.record(False)
            last_error = ProviderUnavailable(f"{provider} returned HTTP {response.status_code}.", provider, reason="http_error")
            time.sleep(min(2 ** attempt, 8))
            continue
        _log_call(provider, endpoint, "ok" if response.ok else "client_error", response.status_code, started, None if response.ok else response.text[:200])
        circuit.record(True)
        return response
    if isinstance(last_error, ProviderUnavailable):
        raise last_error
    raise ProviderUnavailable(f"{provider} could not be reached.", provider, reason="network") from last_error


def json_or_raise(response: requests.Response, provider: str):
    try:
        return response.json()
    except ValueError as error:
        raise MalformedResponse(f"{provider} returned a non-JSON response.", provider) from error


def health_snapshot(provider: str) -> dict:
    from ml.data import store
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    try:
        stats = store.provider_call_stats(provider, since)
    except Exception:
        stats = {}
    return {"circuit": breaker(provider).state, "last_hour": stats}
