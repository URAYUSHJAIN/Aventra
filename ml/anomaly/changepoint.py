"""Change-point detection with ruptures/PELT (Final Plan §10, model D).

RETROSPECTIVE annotation only: PELT segments the whole scoring window, so a
change point at bar t is located using bars after t. It is therefore reported as
regime context in the UI/evidence and is NOT used in the real-time ensemble or
the risk score (that would be look-ahead).
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)
PELT_PENALTY = 12.0   # default; larger -> fewer change points. Not tuned.
PELT_MIN_SIZE = 10


def detect_change_points(features: pd.DataFrame, columns=("log_return", "log_volume")) -> dict:
    try:
        import ruptures as rpt
    except ImportError:
        return {"status": "unavailable", "reason": "ruptures is not installed", "change_points": []}
    frame = features[["trading_date", *columns]].dropna()
    if len(frame) < 3 * PELT_MIN_SIZE:
        return {"status": "insufficient_history", "change_points": []}
    signal = frame[list(columns)].to_numpy(dtype=float)
    signal = (signal - signal.mean(axis=0)) / np.where(signal.std(axis=0) > 0, signal.std(axis=0), 1)
    try:
        breakpoints = rpt.Pelt(model="l2", min_size=PELT_MIN_SIZE).fit(signal).predict(pen=PELT_PENALTY)
    except Exception:  # ruptures raises generic errors on degenerate input
        logger.exception("Change-point detection failed")
        return {"status": "failed", "change_points": []}
    dates = frame["trading_date"].tolist()
    points = [dates[index].strftime("%Y-%m-%d") for index in breakpoints[:-1]]   # last breakpoint is the series end
    return {"status": "ok", "method": "ruptures.Pelt(model='l2')", "penalty": PELT_PENALTY, "signals": list(columns), "retrospective": True, "change_points": points}
