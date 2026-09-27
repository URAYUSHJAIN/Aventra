"""Layer 1 — simple statistical detector (research baseline 1, ML Pipeline §19/§46).

Classic (non-robust, non-adaptive) z-score of the current bar against the mean
and standard deviation of the previous ROLLING_WINDOW bars. Deliberately simpler
than the behavioural fingerprint so the two can be compared.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml import config
from ml.fingerprint.baseline import deviation_score


def rolling_zscores(features: pd.DataFrame, columns=config.STATISTICAL_FEATURES, window: int = config.ROLLING_WINDOW) -> pd.DataFrame:
    out = pd.DataFrame(index=features.index)
    for column in columns:
        prior = features[column].shift(1).rolling(window, min_periods=window)
        std = prior.std().replace(0, np.nan)
        out[f"stat_z_{column}"] = (features[column] - prior.mean()) / std
    return out


def statistical_scores(features: pd.DataFrame) -> pd.DataFrame:
    """Max deviation score over the statistical features (NaN only when every feature is unavailable)."""
    zscores = rolling_zscores(features)
    scores = pd.DataFrame(deviation_score(zscores.to_numpy(dtype=float)), index=zscores.index)
    zscores["statistical_score"] = scores.max(axis=1, skipna=True)
    return zscores
