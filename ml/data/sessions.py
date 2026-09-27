"""Timestamp normalisation and session alignment (calendar-aware; see ml/data/calendars.py).

All timestamps are stored and compared in UTC. The calendar argument defaults to XBOM (the documented NSE proxy)
so v0.1 callers keep their behaviour; the pipeline passes each instrument's own calendar.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from ml import config
from ml.data import calendars

LOCAL_TZ = config.MARKET_TIMEZONE
DEFAULT_CALENDAR = "XBOM"


def to_utc(value) -> pd.Timestamp:
    """Parse a datetime/string/epoch into a tz-aware UTC Timestamp. Naive values are assumed UTC."""
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def iso(ts) -> str | None:
    if ts is None or (isinstance(ts, float) and pd.isna(ts)) or ts is pd.NaT:
        return None
    return to_utc(ts).strftime("%Y-%m-%dT%H:%M:%SZ")


def session_bounds(trading_date, calendar_code: str | None = DEFAULT_CALENDAR) -> tuple[pd.Timestamp, pd.Timestamp]:
    """UTC open/close of the session on a local trading date for the given calendar."""
    return calendars.session_bounds(trading_date, calendar_code)


def local_date(ts, calendar_code: str | None = DEFAULT_CALENDAR, tz_name: str | None = LOCAL_TZ) -> pd.Timestamp:
    return calendars.local_trading_date(ts, calendar_code, tz_name)


def is_session_in_progress(trading_date, now: datetime | None = None, calendar_code: str | None = DEFAULT_CALENDAR) -> bool:
    return calendars.is_session_in_progress(trading_date, calendar_code, now)


def align_to_session(published_utc, trading_dates: list[pd.Timestamp], calendar_code: str | None = DEFAULT_CALENDAR) -> pd.Timestamp | None:
    """Map a publication time to the first observed trading session whose close is at/after it.

    Uses the trading dates actually present in the price data, so holidays are respected without relying on
    the calendar's holiday list. Returns None when the news is newer than the last observed session.
    """
    published = to_utc(published_utc)
    for trading_date in trading_dates:
        if session_bounds(trading_date, calendar_code)[1] >= published:
            return pd.Timestamp(trading_date)
    return None
