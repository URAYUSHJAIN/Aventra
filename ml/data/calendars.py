"""Market calendars per instrument (exchange_calendars for exchanges; explicit rules for 24/7 and 24/5 markets).

Session bounds are used to stamp daily bars and to align news with sessions. Historical session sets always
come from the provider's observed bars (Phase 0: XBOM, used as the NSE proxy, differs from NSE on Muhurat
sessions); the calendar is only used for timing and for "is the session still in progress".
"""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, timezone
from functools import lru_cache

import pandas as pd

logger = logging.getLogger(__name__)
# Fallback local session hours when exchange_calendars cannot answer (e.g. dates outside its range).
FALLBACK_HOURS = {"XBOM": ("Asia/Kolkata", (9, 15), (15, 30)), "XNYS": ("America/New_York", (9, 30), (16, 0))}
ROUND_THE_CLOCK = {"24/7", "24/5"}


@lru_cache(maxsize=16)
def _calendar(code: str):
    try:
        import exchange_calendars as xcals
        return xcals.get_calendar(code)
    except Exception:   # library missing or unknown code: fall back to fixed hours
        logger.warning("exchange_calendars unavailable for %s; using fixed session hours", code)
        return None


def session_bounds(trading_date, calendar_code: str | None) -> tuple[pd.Timestamp, pd.Timestamp]:
    """UTC (open, close) of the session on a local trading date."""
    day = pd.Timestamp(trading_date).date()
    if not calendar_code or calendar_code in ROUND_THE_CLOCK:
        start = pd.Timestamp(datetime.combine(day, time(0, 0)), tz="UTC")
        return start, start + pd.Timedelta(days=1)
    cal = _calendar(calendar_code)
    if cal is not None:
        try:
            label = pd.Timestamp(day)
            if cal.is_session(label):
                return pd.Timestamp(cal.session_open(label)).tz_convert("UTC"), pd.Timestamp(cal.session_close(label)).tz_convert("UTC")
        except Exception:
            pass
    tz, open_hm, close_hm = FALLBACK_HOURS.get(calendar_code, ("UTC", (0, 0), (23, 59)))
    open_local = pd.Timestamp(datetime.combine(day, time(*open_hm))).tz_localize(tz)
    close_local = pd.Timestamp(datetime.combine(day, time(*close_hm))).tz_localize(tz)
    return open_local.tz_convert("UTC"), close_local.tz_convert("UTC")


def session_open_utc(trading_date, calendar_code: str | None) -> pd.Timestamp:
    return session_bounds(trading_date, calendar_code)[0]


def local_trading_date(ts, calendar_code: str | None, tz_name: str | None) -> pd.Timestamp:
    """Local calendar date of a UTC bar timestamp (naive midnight Timestamp)."""
    value = pd.Timestamp(ts)
    value = value.tz_localize("UTC") if value.tzinfo is None else value.tz_convert("UTC")
    if calendar_code in ROUND_THE_CLOCK or not tz_name:
        return value.tz_convert("UTC").normalize().tz_localize(None)
    return value.tz_convert(tz_name).normalize().tz_localize(None)


def is_session_in_progress(trading_date, calendar_code: str | None, now: datetime | None = None) -> bool:
    now_ts = pd.Timestamp(now or datetime.now(timezone.utc))
    now_ts = now_ts.tz_localize("UTC") if now_ts.tzinfo is None else now_ts.tz_convert("UTC")
    open_utc, close_utc = session_bounds(trading_date, calendar_code)
    return open_utc <= now_ts < close_utc + timedelta(minutes=15)
