"""Intelligence results for the API without blocking HTTP requests on expensive analysis.

GET resolution order: fresh stored run (database) → recent terminal job failure (returned as its typed
data-availability state) → enqueue an `analyze` job and return 202 with the job and any older result.
AVENTRA_JOB_MODE: `inline` (default; the API process runs queued jobs on a small thread pool), `external` (a separate
worker service, Docker), `sync` (run inside the request — tests and CLI only).
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from threading import Lock

from ml import config
from ml.data import store
from ml.jobs import queue
from ml.jobs.worker import dispatch
from ml.pipelines.intelligence import resolve_instrument, run_intelligence

logger = logging.getLogger(__name__)
_cache: dict[str, tuple[float, dict]] = {}
_locks: dict[str, Lock] = {}
_registry_lock = Lock()
FAILURE_MEMORY = timedelta(minutes=10)
__all__ = ["get_intelligence", "queue", "dispatch", "resolve_instrument", "AnalysisPending", "AnalysisFailed"]


class AnalysisPending(Exception):
    def __init__(self, job: dict, previous: dict | None):
        super().__init__("analysis queued")
        self.job, self.previous = job, previous


class AnalysisFailed(Exception):
    def __init__(self, code: str, message: str, attempts: list[dict] | None = None):
        super().__init__(message)
        self.code, self.attempts = code, attempts or []


def _lock_for(key: str) -> Lock:
    with _registry_lock:
        return _locks.setdefault(key, Lock())


def job_mode() -> str:
    mode = os.getenv("AVENTRA_JOB_MODE", "inline").strip().lower()
    return mode if mode in {"inline", "external", "sync"} else "inline"


def _fresh(result: dict) -> bool:
    generated = store.utc(result.get("generated_at"))
    return generated is not None and datetime.now(timezone.utc) - generated < timedelta(seconds=config.INTELLIGENCE_CACHE_SECONDS)


def get_intelligence(instrument_id: str, refresh: bool = False) -> dict:
    """Return a result, or raise AnalysisPending (202) / AnalysisFailed (typed state)."""
    resolve_instrument(instrument_id)            # 404 for unknown instruments before anything is queued
    if job_mode() == "sync":
        with _lock_for(instrument_id):
            hit = _cache.get(instrument_id)
            if hit and not refresh and hit[0] > time.monotonic():
                return hit[1]
            result = run_intelligence(instrument_id, force_refresh=refresh)
            _cache[instrument_id] = (time.monotonic() + config.INTELLIGENCE_CACHE_SECONDS, result)
            return result
    stored = store.latest_run(instrument_id)
    if stored and not refresh and _fresh(stored):
        return stored
    last_job = queue.latest_for(f"analyze:{instrument_id}")
    if last_job and last_job["status"] == "failed" and not refresh:
        failed_at = store.utc(last_job["updated_at"])
        if failed_at and datetime.now(timezone.utc) - failed_at < FAILURE_MEMORY:
            code, _, message = (last_job.get("error") or "ANALYSIS_FAILED: analysis failed").partition(": ")
            raise AnalysisFailed(code, message, (last_job.get("result") or {}).get("attempts"))
    job = queue.enqueue("analyze", instrument_id, {"refresh": refresh}, dedupe_key=f"analyze:{instrument_id}", priority=10)
    dispatch()
    raise AnalysisPending(job, stored)


def peek(instrument_id: str) -> dict | None:
    """A cached or stored result without triggering a run (used for detail lookups)."""
    hit = _cache.get(instrument_id)
    return hit[1] if hit else store.latest_run(instrument_id)


def fingerprint_view(result: dict) -> dict:
    return {"instrument_id": result["instrument_id"], "symbol": result["symbol"], "asset": result["asset"], "generated_at": result["generated_at"],
            "data_source": result["data_source"]["market"], **result["fingerprint"]}


def anomaly_view(result: dict) -> dict:
    return {"instrument_id": result["instrument_id"], "symbol": result["symbol"], "generated_at": result["generated_at"], "data_source": result["data_source"]["market"],
            **result["anomaly"], "flagged": [event["anomaly"] for event in result["events"]],
            "series": [{k: row[k] for k in ("date", "close", "anomaly_score", "is_anomaly", "severity")} for row in result["market"]["series"]],
            "models": {"isolation_forest": result["models"]["isolation_forest"]}}


def risk_view(result: dict) -> dict:
    events = result["events"]
    return {"instrument_id": result["instrument_id"], "symbol": result["symbol"], "generated_at": result["generated_at"],
            "current": {"trading_date": result["current_assessment"]["trading_date"], **result["current_assessment"]["risk"]},
            "latest_flagged_event": {"event_id": events[0]["event_id"], "trading_date": events[0]["trading_date"], **events[0]["risk"]} if events else None,
            "disclaimer": result["disclaimer"]}
