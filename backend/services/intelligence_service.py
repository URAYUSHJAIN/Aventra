"""Orchestrates the ML pipeline for the API: per-instrument locking, in-memory cache, persisted results."""
from __future__ import annotations

import logging
import time
from threading import Lock

from ml import config
from ml.data import store
from ml.pipelines.intelligence import run_intelligence

logger = logging.getLogger(__name__)
_cache: dict[str, tuple[float, dict]] = {}
_locks: dict[str, Lock] = {}
_registry_lock = Lock()


def _lock_for(key: str) -> Lock:
    with _registry_lock:
        return _locks.setdefault(key, Lock())


def get_intelligence(instrument_id: str, refresh: bool = False) -> dict:
    """Latest result for an instrument; runs the pipeline when missing, expired or `refresh` is requested.
    Concurrent requests for the same instrument wait for one run instead of starting several."""
    with _lock_for(instrument_id):
        hit = _cache.get(instrument_id)
        if hit and not refresh and hit[0] > time.monotonic():
            return hit[1]
        result = run_intelligence(instrument_id, force_refresh=refresh)
        _cache[instrument_id] = (time.monotonic() + config.INTELLIGENCE_CACHE_SECONDS, result)
        return result


def peek(instrument_id: str) -> dict | None:
    """A cached or stored result without triggering a run (used for detail lookups)."""
    hit = _cache.get(instrument_id)
    return hit[1] if hit else store.latest_run(instrument_id)


def fingerprint_view(result: dict) -> dict:
    return {"instrument_id": result["instrument_id"], "symbol": result["symbol"], "asset": result["asset"], "generated_at": result["generated_at"], "data_source": result["data_source"]["market"], **result["fingerprint"]}


def anomaly_view(result: dict) -> dict:
    return {"instrument_id": result["instrument_id"], "symbol": result["symbol"], "generated_at": result["generated_at"], "data_source": result["data_source"]["market"], **result["anomaly"],
            "flagged": [event["anomaly"] for event in result["events"]], "series": [{k: row[k] for k in ("date", "close", "anomaly_score", "is_anomaly", "severity")} for row in result["market"]["series"]],
            "models": {"isolation_forest": result["models"]["isolation_forest"]}}


def risk_view(result: dict) -> dict:
    events = result["events"]
    return {"instrument_id": result["instrument_id"], "symbol": result["symbol"], "generated_at": result["generated_at"], "current": {"trading_date": result["current_assessment"]["trading_date"], **result["current_assessment"]["risk"]},
            "latest_flagged_event": {"event_id": events[0]["event_id"], "trading_date": events[0]["trading_date"], **events[0]["risk"]} if events else None,
            "disclaimer": result["disclaimer"]}
