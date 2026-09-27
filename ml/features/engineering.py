"""Feature engineering shared by training, inference and evaluation (one definition, no drift).

Leakage rule (ML Pipeline §14): the feature for bar t uses bar t and earlier only. Baselines the current value
is compared against (rolling means/std of volume and price) use bars strictly before t (`shift(1)`), never
centred windows. Features that need data an instrument does not have (volume, OHLC) are left NaN — never
imputed — and the capability-based feature sets (ml/features/sets.py) exclude them.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml import config
from ml.data.calendars import local_trading_date

FEATURE_DEFINITIONS = {
    "return_1": "Close-to-close return versus the previous observation.",
    "log_return": "Natural log of close / previous close.",
    "return_5": "Return over the last 5 observations.",
    "volatility_20": "Standard deviation of log returns over the last 20 observations (including the current one).",
    "log_volume": "log(1 + volume).",
    "volume_ratio": "Volume divided by the mean volume of the previous 20 observations.",
    "volume_zscore": "(Volume - mean of previous 20) / std of previous 20.",
    "gap_pct": "Open versus previous close.",
    "range_pct": "(High - low) divided by previous close.",
    "ma20_distance": "Close versus the mean close of the previous 20 observations.",
    "rsi_14": "Wilder RSI over 14 observations (causal exponential smoothing).",
    "drawdown": "Close versus the running maximum close up to this observation (0 at a new high).",
    "relative_return": "Return minus the benchmark's return for the same trading date (NaN when no benchmark).",
    "change_bp": "Yield change versus the previous observation, in basis points.",
    "change_5_bp": "Yield change over the last 5 observations, in basis points.",
    "volatility_bp_20": "Standard deviation of daily yield changes over the last 20 observations, in basis points.",
    "level_distance_bp": "Yield level versus the mean of the previous 20 observations, in basis points.",
}


def compute_features(bars: pd.DataFrame, benchmark: pd.DataFrame | None = None, profile: dict | None = None) -> pd.DataFrame:
    """bars: validated observations sorted by timestamp. profile: capability profile (calendar, timezone, value_kind)."""
    profile = profile or {}
    calendar, tz = profile.get("calendar", "XBOM"), profile.get("timezone", config.MARKET_TIMEZONE)
    columns = ["timestamp", "open", "high", "low", "close", "volume"]
    df = bars.reindex(columns=columns).copy().reset_index(drop=True)
    df["trading_date"] = [local_trading_date(ts, calendar, tz) for ts in df["timestamp"]]
    close, volume = df["close"].astype(float), df["volume"].astype(float)
    prev_close = close.shift(1)
    window = config.ROLLING_WINDOW

    if profile.get("value_kind") == "yield":
        # Yields/rates: level changes in basis points (percentage returns of a yield are not meaningful).
        change_bp = (close - prev_close) * 100
        df["change_bp"] = change_bp
        df["change_5_bp"] = (close - close.shift(5)) * 100
        df["volatility_bp_20"] = change_bp.rolling(window, min_periods=window).std()
        df["level_distance_bp"] = (close - prev_close.rolling(window, min_periods=window).mean()) * 100
        for name in ("return_1", "log_return", "return_5", "volatility_20", "ma20_distance", "rsi_14", "drawdown", "log_volume", "volume_ratio",
                     "volume_zscore", "gap_pct", "range_pct", "relative_return"):
            df[name] = np.nan
        return df.replace([np.inf, -np.inf], np.nan)

    df["return_1"] = close / prev_close - 1
    df["log_return"] = np.log(close / prev_close)
    df["return_5"] = close / close.shift(5) - 1
    df["volatility_20"] = df["log_return"].rolling(window, min_periods=window).std()
    df["log_volume"] = np.log1p(volume)
    prior_volume = volume.shift(1).rolling(window, min_periods=window)
    prior_mean, prior_std = prior_volume.mean(), prior_volume.std()
    df["volume_ratio"] = volume / prior_mean.replace(0, np.nan)
    df["volume_zscore"] = (volume - prior_mean) / prior_std.replace(0, np.nan)
    df["gap_pct"] = df["open"] / prev_close - 1
    df["range_pct"] = (df["high"] - df["low"]) / prev_close
    df["ma20_distance"] = close / prev_close.rolling(window, min_periods=window).mean() - 1
    df["rsi_14"] = _rsi(close, config.RSI_WINDOW)
    df["drawdown"] = close / close.cummax() - 1
    for name in ("change_bp", "change_5_bp", "volatility_bp_20", "level_distance_bp"):
        df[name] = np.nan

    if benchmark is not None and not benchmark.empty:
        bench = benchmark[["timestamp", "close"]].copy()
        bench["trading_date"] = [local_trading_date(ts, calendar, tz) for ts in bench["timestamp"]]
        bench = bench.drop_duplicates("trading_date", keep="last").set_index("trading_date")["close"]
        bench_return = bench / bench.shift(1) - 1
        df["relative_return"] = df["return_1"] - df["trading_date"].map(bench_return)
    else:
        df["relative_return"] = np.nan
    return df.replace([np.inf, -np.inf], np.nan)


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = gains / losses.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    return rsi.where(losses != 0, 100.0).where(gains.notna())
