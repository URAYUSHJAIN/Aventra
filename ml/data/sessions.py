"""Timestamp normalisation and NSE session alignment.

All timestamps are stored and compared in UTC. Local (Asia/Kolkata) time is used
only to derive session boundaries and for display.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

import pandas as pd

from ml import config

LOCAL_TZ = config.MARKET_TIMEZONE


def to_utc(value) -> pd.Timestamp:
    """Parse a datetime/string/epoch into a tz-aware UTC Timestamp. Naive values are assumed UTC."""
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def iso(ts) -> str | None:
    if ts is None or (isinstance(ts, float) and pd.isna(ts)) or ts is pd.NaT:
        return None
    return to_utc(ts).strftime("%Y-%m-%dT%H:%M:%SZ")


def session_bounds(trading_date) -> tuple[pd.Timestamp, pd.Timestamp]:
    """UTC open/close of the NSE regular session on a local trading date."""
    day = pd.Timestamp(trading_date).date()
    open_local = pd.Timestamp(datetime.combine(day, time(*config.SESSION_OPEN))).tz_localize(LOCAL_TZ)
    close_local = pd.Timestamp(datetime.combine(day, time(*config.SESSION_CLOSE))).tz_localize(LOCAL_TZ)
    return open_local.tz_convert("UTC"), close_local.tz_convert("UTC")


def local_date(ts) -> pd.Timestamp:
    return to_utc(ts).tz_convert(LOCAL_TZ).normalize().tz_localize(None)


def is_session_in_progress(trading_date, now: datetime | None = None) -> bool:
    now_utc = to_utc(now or datetime.now(timezone.utc))
    open_utc, close_utc = session_bounds(trading_date)
    return open_utc <= now_utc < close_utc + timedelta(minutes=15)


def align_to_session(published_utc, trading_dates: list[pd.Timestamp]) -> pd.Timestamp | None:
    """Map a publication time to the first observed trading session whose close is at/after it.

    Uses the trading dates actually present in the price data, so exchange holidays
    are respected without a hard-coded calendar. Returns None when the news is newer
    than the last observed session.
    """
    published = to_utc(published_utc)
    for trading_date in trading_dates:
        if session_bounds(trading_date)[1] >= published:
            return pd.Timestamp(trading_date)
    return None
