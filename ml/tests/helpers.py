"""Small deterministic fixtures for ML tests (no network)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def make_bars(n: int = 400, seed: int = 7, start: str = "2024-01-01") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start=start, periods=n)
    close = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    prev = np.concatenate([[100.0], close[:-1]])
    open_ = prev * (1 + rng.normal(0, 0.002, n))
    high = np.maximum(open_, close) * 1.005
    low = np.minimum(open_, close) * 0.995
    volume = np.exp(rng.normal(np.log(1e6), 0.2, n))
    ts = [pd.Timestamp(d).tz_localize("Asia/Kolkata").replace(hour=9, minute=15).tz_convert("UTC") for d in days]
    return pd.DataFrame({"timestamp": ts, "open": open_, "high": high, "low": low, "close": close, "volume": volume, "symbol": "TEST", "source": "fixture"})
