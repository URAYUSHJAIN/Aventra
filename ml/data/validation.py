"""Capability-aware validation and cleaning of normalised observations.

Only *data errors* are removed (duplicates, missing values, impossible OHLC ranges, non-positive prices where
prices must be positive, provider holiday placeholders). Extreme but valid movements are kept: they may be the
anomalies Aventra exists to detect. OHLC/volume rules apply only when the instrument's profile has OHLC/volume;
yield series may be zero or negative.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("timestamp", "close")
CORPORATE_ACTION_THRESHOLD = 0.35   # single-bar move flagged for review (possible split/bonus in unadjusted data)
DEFAULT_PROFILE = {"has_ohlc": True, "has_volume": True, "value_kind": "price"}


class MarketDataError(ValueError):
    """The market data cannot be used (missing columns, empty after cleaning)."""


def validate_series(frame: pd.DataFrame, instrument_id: str = "", profile: dict | None = None, max_staleness_days: int | None = None) -> tuple[pd.DataFrame, dict]:
    """Return (clean_frame, report). `profile` = capability profile (has_ohlc, has_volume, value_kind)."""
    profile = {**DEFAULT_PROFILE, **(profile or {})}
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise MarketDataError(f"Market data is missing columns: {', '.join(missing)}")
    df = frame.copy()
    for column in ("open", "high", "low", "close", "volume"):
        df[column] = pd.to_numeric(df[column], errors="coerce") if column in df.columns else np.nan
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

    report: dict = {"instrument_id": instrument_id, "rows_in": int(len(df)), "profile": {k: profile[k] for k in ("has_ohlc", "has_volume", "value_kind")}}
    checked = ["timestamp", "close"] + (["open", "high", "low"] if profile["has_ohlc"] else []) + (["volume"] if profile["has_volume"] else [])
    report["missing_values"] = {column: int(df[column].isna().sum()) for column in checked}
    report["out_of_order"] = bool(not df["timestamp"].dropna().is_monotonic_increasing)
    report["timestamp_errors"] = int(df["timestamp"].isna().sum())

    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    before = len(df)
    df = df.drop_duplicates(subset=["timestamp"], keep="last")
    report["duplicates_removed"] = int(before - len(df))

    missing_close = df["close"].isna()
    positive_required = profile["value_kind"] not in {"yield"}
    non_positive = (df["close"] <= 0) if positive_required else pd.Series(False, index=df.index)
    if profile["has_ohlc"]:
        prices = df[["open", "high", "low", "close"]]
        if positive_required:
            non_positive = non_positive | (prices.fillna(1) <= 0).any(axis=1)
        impossible = (df["high"] < df["low"]) | (df["high"] < df[["open", "close"]].max(axis=1) * (1 - 1e-6)) | (df["low"] > df[["open", "close"]].min(axis=1) * (1 + 1e-6))
        impossible = impossible.fillna(False)
    else:
        impossible = pd.Series(False, index=df.index)
    invalid = missing_close | non_positive | impossible
    report["invalid_rows_removed"] = {   # exclusive categories: each removed row is counted once
        "missing_price": int(missing_close.sum()), "non_positive_price": int((non_positive & ~missing_close).sum()),
        "impossible_ohlc": int((impossible & ~missing_close & ~non_positive).sum()),
    }
    df = df[~invalid]

    if profile["has_volume"]:
        # Provider placeholder bars on exchange holidays: no volume and no price range (O=H=L=C). Not trading data.
        placeholder = (df["volume"] == 0) & (df["high"] == df["low"]) if profile["has_ohlc"] else pd.Series(False, index=df.index)
        report["holiday_placeholders_removed"] = int(placeholder.sum())
        df = df[~placeholder]
        negative_volume = df["volume"] < 0
        df.loc[negative_volume, "volume"] = np.nan
        report["negative_volume_set_missing"] = int(negative_volume.sum())
        report["zero_volume_bars"] = int((df["volume"] == 0).sum())
        report["volume_missing_bars"] = int(df["volume"].isna().sum())
    else:
        df["volume"] = np.nan   # never invent volume for series that do not have it
        report["holiday_placeholders_removed"] = 0

    if profile["value_kind"] != "yield":
        moves = df["close"].pct_change().abs()
        report["large_moves_flagged"] = [ts.strftime("%Y-%m-%d") for ts in df.loc[moves > CORPORATE_ACTION_THRESHOLD, "timestamp"]]
    else:
        report["large_moves_flagged"] = []
    gaps = df["timestamp"].diff().dt.days
    report["calendar_gaps_over_5_days"] = int((gaps > 5).sum())
    report["rows_out"] = int(len(df))
    if df.empty:
        raise MarketDataError("No valid observations remain after validation.")
    last = df["timestamp"].iloc[-1]
    report["last_observation"] = last.strftime("%Y-%m-%dT%H:%M:%SZ")
    age_days = (pd.Timestamp.now(tz="UTC") - last).days
    report["age_days"] = int(age_days)
    report["stale"] = bool(max_staleness_days is not None and age_days > max_staleness_days)
    if report["rows_in"] != report["rows_out"]:
        logger.info("Validation for %s removed %d of %d rows", instrument_id, report["rows_in"] - report["rows_out"], report["rows_in"])
    return df.reset_index(drop=True), report


def validate_ohlcv(frame: pd.DataFrame, symbol: str = "") -> tuple[pd.DataFrame, dict]:
    """Backward-compatible OHLCV validation (equity profile)."""
    return validate_series(frame, symbol, DEFAULT_PROFILE)
