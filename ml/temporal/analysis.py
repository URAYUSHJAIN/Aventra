"""Temporal analysis: ordered event timelines and lead/lag association (ML Pipeline §25–26).

Lead/lag values are correlations between daily series at different offsets. They
describe association in time only and are reported with their sample size.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.data.sessions import iso, to_utc

MIN_LEAD_LAG_DAYS = 20


def build_timeline(items: list[dict]) -> list[dict]:
    """items: [{timestamp, type, source, description}] → sorted with gap (minutes) from the previous item."""
    ordered = sorted((item for item in items if item.get("timestamp")), key=lambda item: to_utc(item["timestamp"]))
    previous = None
    for item in ordered:
        current = to_utc(item["timestamp"])
        item["gap_minutes_from_previous"] = None if previous is None else round((current - previous).total_seconds() / 60, 1)
        previous = current
    return ordered


def lead_lag(daily_returns: pd.Series, daily_sentiment: pd.Series, max_lag: int = 3) -> dict:
    """Pearson correlation of sentiment(t) with return(t + lag) for lag in [-max_lag, max_lag].

    Positive lag = sentiment leads returns. Requires MIN_LEAD_LAG_DAYS overlapping days.
    """
    joined = pd.concat({"ret": daily_returns, "sent": daily_sentiment}, axis=1).dropna(subset=["ret"])
    days_with_news = int(joined["sent"].notna().sum())
    if days_with_news < MIN_LEAD_LAG_DAYS:
        return {"status": "insufficient_data", "days_with_news": days_with_news, "required": MIN_LEAD_LAG_DAYS, "lags": []}
    lags = []
    for lag in range(-max_lag, max_lag + 1):
        pair = pd.concat([joined["sent"], joined["ret"].shift(-lag)], axis=1).dropna()
        if len(pair) >= MIN_LEAD_LAG_DAYS and pair.iloc[:, 0].std() > 0 and pair.iloc[:, 1].std() > 0:
            lags.append({"lag_days": lag, "correlation": round(float(np.corrcoef(pair.iloc[:, 0], pair.iloc[:, 1])[0, 1]), 4), "n": int(len(pair))})
    return {
        "status": "ok", "days_with_news": days_with_news, "lags": lags,
        "interpretation": "Correlation between daily mean news sentiment and daily returns at each offset; association only, not causation.",
    }


def session_relation_text(hours: float, relation: str) -> str:
    if relation == "published_during_session":
        return "published during the trading session"
    if relation == "published_before_session":
        return f"published {abs(hours):.1f} h before the session opened"
    return f"published {hours:.1f} h after the session closed"


__all__ = ["build_timeline", "lead_lag", "session_relation_text", "iso"]
