"""Feature engineering shared by training, inference and evaluation (one definition, no drift).

Leakage rule (ML Pipeline §14): the feature for bar t uses bar t and earlier only.
Baselines that the current value is compared against (rolling means/std of volume
and price) use bars strictly before t (`shift(1)`), never centred windows.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml import config
from ml.data.sessions import local_date

FEATURE_DEFINITIONS = {
    "return_1": "Close-to-close return versus the previous bar.",
    "log_return": "Natural log of close / previous close.",
    "return_5": "Return over the last 5 bars.",
    "volatility_20": "Standard deviation of log returns over the last 20 bars (including the current bar).",
    "log_volume": "log(1 + volume).",
    "volume_ratio": "Volume divided by the mean volume of the previous 20 bars.",
    "volume_zscore": "(Volume - mean of previous 20 bars) / std of previous 20 bars.",
    "gap_pct": "Open versus previous close.",
    "range_pct": "(High - low) divided by previous close.",
    "ma20_distance": "Close versus the mean close of the previous 20 bars.",
    "rsi_14": "Wilder RSI over 14 bars (causal exponential smoothing).",
    "relative_return": "Return minus the NIFTY 50 return for the same trading date (NaN when the benchmark is unavailable).",
}


def compute_features(bars: pd.DataFrame, benchmark: pd.DataFrame | None = None) -> pd.DataFrame:
    """bars: validated OHLCV sorted by timestamp. benchmark: optional validated OHLCV of the benchmark index."""
    df = bars[["timestamp", "open", "high", "low", "close", "volume"]].copy().reset_index(drop=True)
    df["trading_date"] = df["timestamp"].map(local_date)
    close, volume = df["close"], df["volume"].astype(float)
    prev_close = close.shift(1)
    window = config.ROLLING_WINDOW

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

    if benchmark is not None and not benchmark.empty:
        bench = benchmark[["timestamp", "close"]].copy()
        bench["trading_date"] = bench["timestamp"].map(local_date)
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
