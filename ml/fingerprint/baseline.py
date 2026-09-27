"""Adaptive behavioural fingerprint (ML Pipeline §15–18, Final Plan §9).

For every behavioural dimension the baseline at bar t is the rolling median and
MAD of the previous FINGERPRINT_WINDOW bars (bar t itself excluded). The robust
z-score of bar t measures its deviation from the asset's own normal behaviour.

Guarded adaptive update: an observation whose |z| exceeds FINGERPRINT_GUARD_Z
enters the baseline history clipped to median ± guard × scale, so a single extreme
event cannot redefine "normal", while a persistent regime shift is still absorbed
gradually.
"""
from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd

from ml import config

MAD_TO_STD = 1.4826   # consistency constant: MAD * 1.4826 estimates sigma for normal data
EPS = 1e-12


def deviation_score(z: np.ndarray | float) -> np.ndarray | float:
    """Map |robust z| to [0, 1]: 0 at/below Z_SCORE_FLOOR, 1 at/above Z_SCORE_CAP (linear in between)."""
    return np.clip((np.abs(z) - config.Z_SCORE_FLOOR) / (config.Z_SCORE_CAP - config.Z_SCORE_FLOOR), 0.0, 1.0)


def rolling_robust_baseline(values: np.ndarray, window: int = config.FINGERPRINT_WINDOW, min_history: int = config.FINGERPRINT_MIN_HISTORY,
                            guard_z: float = config.FINGERPRINT_GUARD_Z) -> dict[str, np.ndarray]:
    n = len(values)
    median, scale, z = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    history: deque[float] = deque(maxlen=window)
    for t, value in enumerate(values):
        if len(history) >= min_history:
            hist = np.fromiter(history, dtype=float)
            med = float(np.median(hist))
            robust = MAD_TO_STD * float(np.median(np.abs(hist - med)))
            if robust < EPS:   # flat history (e.g. many identical values): fall back to std, then epsilon
                robust = float(hist.std()) or EPS
            median[t], scale[t] = med, robust
            if not np.isnan(value):
                z[t] = (value - med) / robust
        if np.isnan(value):
            continue
        if not np.isnan(z[t]) and abs(z[t]) > guard_z:
            history.append(median[t] + np.sign(z[t]) * guard_z * scale[t])   # guarded update
        else:
            history.append(float(value))
    return {"median": median, "scale": scale, "z": z, "final_history": np.fromiter(history, dtype=float)}


def compute_fingerprint(features: pd.DataFrame, weights: dict[str, float] | None = None) -> tuple[pd.DataFrame, dict]:
    """Return (per-bar frame with z/median/scale/score per dimension + fingerprint_score, latest profile)."""
    weights = weights or config.FINGERPRINT_WEIGHTS
    dims = [dim for dim in weights if dim in features.columns and features[dim].notna().any()]
    out = pd.DataFrame(index=features.index)
    profile_dims = {}
    for dim in dims:
        result = rolling_robust_baseline(features[dim].to_numpy(dtype=float))
        out[f"z_{dim}"], out[f"median_{dim}"], out[f"scale_{dim}"] = result["z"], result["median"], result["scale"]
        out[f"score_{dim}"] = deviation_score(result["z"])
        hist = result["final_history"]
        profile_dims[dim] = {"p05": float(np.quantile(hist, 0.05)) if len(hist) else None, "p95": float(np.quantile(hist, 0.95)) if len(hist) else None}

    score_cols = [f"score_{dim}" for dim in dims]
    w = np.array([weights[dim] for dim in dims], dtype=float)
    scores = out[score_cols].to_numpy(dtype=float) if dims else np.empty((len(out), 0))
    available = ~np.isnan(scores)
    weight_sum = (available * w).sum(axis=1)
    weighted = np.where(available, scores, 0.0) @ w if dims else np.zeros(len(out))
    enough = available.sum(axis=1) >= max(1, int(np.ceil(len(dims) / 2)))
    out["fingerprint_score"] = np.where(enough & (weight_sum > 0), weighted / np.where(weight_sum > 0, weight_sum, 1), np.nan)
    out["fingerprint_status"] = np.where(out["fingerprint_score"].isna(), "insufficient_history", "ok")
    return out, {"dimensions": dims, "weights": {dim: weights[dim] for dim in dims}, "quantiles": profile_dims}


def fingerprint_level(score: float | None) -> str:
    if score is None or np.isnan(score):
        return "insufficient_history"
    return next(label for floor, label in config.FINGERPRINT_LEVELS if score >= floor)
