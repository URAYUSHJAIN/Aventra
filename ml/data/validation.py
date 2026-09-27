"""Validation and cleaning for OHLCV bars.

Only *data errors* are removed (duplicates, missing/non-positive prices, impossible
OHLC ranges). Extreme but valid movements are kept: they may be the anomalies
Aventra exists to detect.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")
CORPORATE_ACTION_THRESHOLD = 0.35   # single-bar close move flagged for review (possible split/bonus in unadjusted data)


class MarketDataError(ValueError):
    """The market data cannot be used (missing columns, empty after cleaning)."""


def validate_ohlcv(frame: pd.DataFrame, symbol: str = "") -> tuple[pd.DataFrame, dict]:
    """Return (clean_frame, report). The report lists every issue found and every row removed."""
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise MarketDataError(f"Market data is missing columns: {', '.join(missing)}")

    df = frame.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    for column in ("open", "high", "low", "close", "volume"):
        df[column] = pd.to_numeric(df[column], errors="coerce")

    report: dict = {"symbol": symbol, "rows_in": int(len(df))}
    report["missing_values"] = {column: int(df[column].isna().sum()) for column in REQUIRED_COLUMNS}
    report["out_of_order"] = bool(not df["timestamp"].dropna().is_monotonic_increasing)

    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    before = len(df)
    df = df.drop_duplicates(subset=["timestamp"], keep="last")
    report["duplicates_removed"] = int(before - len(df))

    price_cols = ["open", "high", "low", "close"]
    missing_price = df[price_cols].isna().any(axis=1)
    non_positive = (df[price_cols] <= 0).any(axis=1)
    impossible_range = (df["high"] < df["low"]) | (df["high"] < df[["open", "close"]].max(axis=1) * (1 - 1e-6)) | (df["low"] > df[["open", "close"]].min(axis=1) * (1 + 1e-6))
    invalid = missing_price | non_positive | impossible_range
    report["invalid_rows_removed"] = {
        # exclusive categories: each removed row is counted once
        "missing_price": int(missing_price.sum()), "non_positive_price": int((non_positive & ~missing_price).sum()),
        "impossible_ohlc": int((impossible_range & ~missing_price & ~non_positive).sum()),
    }
    df = df[~invalid]

    # Provider placeholder bars on exchange holidays: no volume and no price range (O=H=L=C). Not trading data.
    placeholder = (df["volume"] == 0) & (df["high"] == df["low"])
    report["holiday_placeholders_removed"] = int(placeholder.sum())
    df = df[~placeholder]

    negative_volume = df["volume"] < 0
    df.loc[negative_volume, "volume"] = np.nan
    report["negative_volume_set_missing"] = int(negative_volume.sum())
    report["zero_volume_bars"] = int((df["volume"] == 0).sum())

    moves = df["close"].pct_change().abs()
    flagged = df.loc[moves > CORPORATE_ACTION_THRESHOLD, "timestamp"]
    report["large_moves_flagged"] = [ts.strftime("%Y-%m-%d") for ts in flagged]   # kept, but surfaced for review

    gaps = df["timestamp"].diff().dt.days
    report["calendar_gaps_over_5_days"] = int((gaps > 5).sum())
    report["rows_out"] = int(len(df))
    if df.empty:
        raise MarketDataError("No valid market observations remain after validation.")
    if report["rows_in"] != report["rows_out"]:
        logger.info("Validation for %s removed %d of %d rows", symbol, report["rows_in"] - report["rows_out"], report["rows_in"])
    return df.reset_index(drop=True), report
