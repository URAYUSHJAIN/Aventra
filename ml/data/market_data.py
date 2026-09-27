"""Market-data access for the pipeline: Instrument Master → provider router → database cache → validation.

- Fresh stored data is reused; otherwise the router is asked for new observations (incremental from the last
  stored bar of the same provider) and the result is stored with full provenance.
- If every legitimate provider fails, previously stored data (never legacy/excluded providers) is used and marked
  `stale`; if nothing is stored, DataUnavailable propagates. Nothing is ever synthesised.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from ml import config
from ml.data import store
from ml.data.calendars import is_session_in_progress, local_trading_date
from ml.data.validation import validate_series
from ml.instruments.profiles import profile_for
from ml.providers import registry

logger = logging.getLogger(__name__)
REFRESH_AFTER = timedelta(hours=6)
STALENESS_DAYS = {"24/7": 3, "24/5": 5}
DEFAULT_STALENESS_DAYS = 10
HISTORY_YEARS = 5


def capability_profile(instrument: dict) -> dict:
    profile = profile_for(instrument["asset_class"], instrument.get("capabilities") or {})
    profile.update(calendar=instrument.get("calendar_code"), timezone=instrument.get("timezone"), currency=instrument.get("currency"))
    return profile


def _stored(instrument_id: str) -> pd.DataFrame:
    frame = store.load_prices(instrument_id)
    if frame.empty:
        return frame
    # One provider per series: prefer the provider with the most recent retrieval.
    provider = frame.sort_values("retrieved_at")["provider"].iloc[-1]
    return frame[frame["provider"] == provider].copy()


def _to_rows(series, instrument_id: str) -> pd.DataFrame:
    frame = series.frame.copy()
    frame["instrument_id"], frame["interval"], frame["provider"], frame["provider_symbol"] = instrument_id, series.interval, series.provider, series.provider_symbol
    frame["currency"], frame["timezone"], frame["adjusted"] = series.currency, series.timezone, series.adjusted
    frame["quality"] = "ok"
    return frame


def load_series(instrument: dict, force_refresh: bool = False) -> tuple[pd.DataFrame, dict, dict]:
    """(validated bars, source/provenance, validation report). Raises registry.DataUnavailable."""
    iid = instrument["instrument_id"]
    profile = capability_profile(instrument)
    stored = _stored(iid)
    now = datetime.now(timezone.utc)
    source = {"stale": False, "notes": [], "attempts": []}
    fresh = not stored.empty and (now - stored["retrieved_at"].max().to_pydatetime()) < REFRESH_AFTER
    if fresh and not force_refresh:
        frame, source["cache"] = stored, "database"
    else:
        start = None
        if not stored.empty:
            start = (stored["timestamp"].max() - pd.Timedelta(days=10)).date()
        else:
            start = (now - timedelta(days=365 * HISTORY_YEARS)).date()
        try:
            series, attempts = registry.fetch_history(instrument, start)
            source["attempts"] = attempts
            if not stored.empty and series.provider != stored["provider"].iloc[0]:
                series, attempts = registry.fetch_history(instrument, (now - timedelta(days=365 * HISTORY_YEARS)).date())   # full series from the new provider
                source["attempts"] += attempts
            store.upsert_prices(_to_rows(series, iid))
            frame = _stored(iid)
            source["cache"] = "refreshed"
            source["meta"] = series.meta
        except registry.DataUnavailable as error:
            if stored.empty:
                raise
            frame = stored
            source.update(stale=True, cache="database", attempts=error.attempts)
            source["notes"].append("Live providers unavailable; showing previously stored observations.")
    if frame.empty:
        raise registry.DataUnavailable("Data unavailable / insufficient source data: no usable observations are stored for this instrument.",
                                       "INSUFFICIENT_SOURCE_DATA", source["attempts"])
    first = frame.iloc[-1]
    source.update(provider=first["provider"], provider_symbol=first["provider_symbol"], currency=first.get("currency") or instrument.get("currency"),
                  timezone=instrument.get("timezone") or first.get("timezone"), adjusted=bool(first.get("adjusted")), value_kind=profile["value_kind"],
                  fetched_at=store.iso(frame["retrieved_at"].max()), calendar=instrument.get("calendar_code"))
    if source["provider"] == "fred":
        from ml.providers.reference_rates import FRED_ATTRIBUTION
        source["attribution"] = FRED_ATTRIBUTION
    staleness = STALENESS_DAYS.get(instrument.get("calendar_code") or "", DEFAULT_STALENESS_DAYS)
    bars, report = validate_series(frame, iid, profile, max_staleness_days=staleness)
    last_date = local_trading_date(bars["timestamp"].iloc[-1], instrument.get("calendar_code"), instrument.get("timezone"))
    if is_session_in_progress(last_date, instrument.get("calendar_code")):
        bars = bars.iloc[:-1]
        source["notes"].append("The in-progress session was excluded: daily analytics use completed sessions only.")
    if report["stale"]:
        source["notes"].append(f"The latest observation is {report['age_days']} days old.")
    return bars.reset_index(drop=True), source, report
