"""Ensemble anomaly score (ML Pipeline §21–22).

anomaly_score = w_stat * statistical + w_fp * fingerprint + w_if * isolation_forest
Weights (config.ENSEMBLE_WEIGHTS) sum to 1 and are defaults, not validated optima.
If a component is unavailable for a bar, the remaining weights are renormalised
and the bar records which components were used.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml import config

COMPONENTS = ("statistical", "fingerprint", "isolation_forest")


def combine(component_scores: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    weights = weights or config.ENSEMBLE_WEIGHTS
    matrix = component_scores[list(COMPONENTS)].to_numpy(dtype=float)
    w = np.array([weights[c] for c in COMPONENTS])
    available = ~np.isnan(matrix)
    weight_sum = (available * w).sum(axis=1)
    score = np.where(weight_sum > 0, (np.where(available, matrix, 0.0) @ w) / np.where(weight_sum > 0, weight_sum, 1), np.nan)
    out = pd.DataFrame(index=component_scores.index)
    out["anomaly_score"] = score
    # Agreement: 1 when all available detectors give the same score, 0 when they span the full [0, 1] range.
    spread = np.full(len(matrix), np.nan)
    rows = available.any(axis=1)
    if rows.any():
        masked = np.where(available[rows], matrix[rows], np.nan)
        spread[rows] = np.nanmax(masked, axis=1) - np.nanmin(masked, axis=1)
    out["model_agreement"] = 1 - spread
    out["components_available"] = available.sum(axis=1)
    out["is_anomaly"] = out["anomaly_score"] >= config.ANOMALY_THRESHOLD
    out["severity"] = [config.severity_for(s) if not np.isnan(s) else None for s in score]
    return out
