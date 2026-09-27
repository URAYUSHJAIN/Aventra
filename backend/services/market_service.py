"""Market snapshots and history for the API, built on the provider router and database cache.

A snapshot is the latest completed observation of an instrument's own series (daily close/NAV/reference rate),
its previous observation and a short series for sparklines — all from real provider data. Failures are returned
as explicit data-availability states; nothing is invented.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from ml import config
from ml.data import cache, store
from ml.data.market_data import load_series
from ml.instruments import ids
from ml.pipelines.intelligence import InsufficientHistory, UnknownAsset, resolve_instrument
from ml.providers import registry

logger = logging.getLogger(__name__)
SNAPSHOT_WORKERS = 4
SPARK_POINTS = 60


def _public_instrument(instrument: dict) -> dict:
    return {k: instrument.get(k) for k in ("instrument_id", "symbol", "name", "asset_class", "exchange", "country", "currency", "timezone", "capabilities")}


def snapshot(instrument_id: str) -> dict:
    def build():
        instrument = resolve_instrument(instrument_id)
        bars, source, report = load_series(instrument)
        last, prev = bars.iloc[-1], (bars.iloc[-2] if len(bars) > 1 else None)
        change = None if prev is None or not prev["close"] else (last["close"] - prev["close"]) / prev["close"] * 100
        change_bp = None if prev is None else (last["close"] - prev["close"]) * 100
        tail = bars.tail(SPARK_POINTS)
        return {
            "instrument": _public_instrument(instrument), "as_of": store.iso(last["timestamp"]), "value_kind": source["value_kind"],
            "last": float(last["close"]), "previous": None if prev is None else float(prev["close"]),
            "change_pct": None if change is None or source["value_kind"] == "yield" else round(float(change), 4),
            "change_bp": round(float(change_bp), 3) if source["value_kind"] == "yield" and change_bp is not None else None,
            "volume": None if last["volume"] != last["volume"] else float(last["volume"]),
            "series": [{"timestamp": store.iso(ts), "close": round(float(c), 6)} for ts, c in zip(tail["timestamp"], tail["close"])],
            "interval": "1d", "data_source": {k: source.get(k) for k in ("provider", "provider_symbol", "fetched_at", "stale", "currency", "adjusted", "notes", "attribution")},
            "quality": {k: report.get(k) for k in ("stale", "age_days", "rows_out")},
        }
    return cache.get_or_set(f"snapshot:{instrument_id}", config.QUOTE_CACHE_SECONDS, build)


def _snapshot_or_state(raw_id: str) -> dict:
    try:
        iid = str(ids.parse(raw_id))
        return {"instrument_id": iid, "status": "ok", "snapshot": snapshot(iid)}
    except ids.InvalidInstrumentId as error:
        return {"instrument_id": raw_id, "status": "INVALID_INSTRUMENT_ID", "error": str(error), "snapshot": None}
    except UnknownAsset as error:
        return {"instrument_id": raw_id, "status": "INSTRUMENT_NOT_FOUND", "error": str(error), "snapshot": None}
    except registry.DataUnavailable as error:
        return {"instrument_id": raw_id, "status": error.code, "error": str(error), "attempts": error.attempts, "snapshot": None}
    except (InsufficientHistory, ValueError) as error:
        return {"instrument_id": raw_id, "status": "INSUFFICIENT_SOURCE_DATA", "error": str(error), "snapshot": None}


def snapshots(instrument_ids: list[str]) -> list[dict]:
    """Batch snapshots, fetched concurrently (bounded); each item carries its own availability state."""
    with ThreadPoolExecutor(max_workers=SNAPSHOT_WORKERS) as pool:
        return list(pool.map(_snapshot_or_state, instrument_ids))


def history(instrument_id: str, limit: int) -> dict:
    instrument = resolve_instrument(instrument_id)
    bars, source, report = load_series(instrument)
    tail = bars.tail(limit)
    return {
        "instrument": _public_instrument(instrument), "interval": "1d", "data_source": source, "validation": report,
        "bars": [{"timestamp": store.iso(r.timestamp), "open": _f(r.open), "high": _f(r.high), "low": _f(r.low), "close": _f(r.close), "volume": _f(r.volume)}
                 for r in tail.itertuples(index=False)],
    }


def _f(value):
    return None if value is None or value != value else round(float(value), 6)
