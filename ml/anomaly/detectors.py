"""Layer 3 — unsupervised ML detectors fitted on past data only.

Scores are converted to [0, 1] with the empirical CDF of the *training* scores:
a bar scoring above ML_SCORE_PERCENTILE_FLOOR of training bars gets a positive
score that reaches 1 beyond the most extreme training bar. The mapping is fitted
on training data only, so no future information leaks into it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import RobustScaler

from ml import config


class InsufficientTrainingData(ValueError):
    pass


@dataclass
class EcdfNormalizer:
    floor: float = config.ML_SCORE_PERCENTILE_FLOOR
    reference: np.ndarray = field(default_factory=lambda: np.array([]))

    def fit(self, raw_train: np.ndarray) -> "EcdfNormalizer":
        self.reference = np.sort(raw_train[~np.isnan(raw_train)])
        return self

    def percentile(self, raw: np.ndarray) -> np.ndarray:
        pct = np.searchsorted(self.reference, raw, side="right") / max(len(self.reference), 1)
        return np.where(np.isnan(raw), np.nan, pct)

    def transform(self, raw: np.ndarray) -> np.ndarray:
        return np.clip((self.percentile(raw) - self.floor) / (1 - self.floor), 0.0, 1.0)


@dataclass
class UnsupervisedDetector:
    """Wraps scaler + model + normaliser. `kind` is 'isolation_forest' or 'lof'."""

    kind: str
    feature_columns: list[str] = field(default_factory=list)
    scaler: RobustScaler | None = None
    model: object | None = None
    normalizer: EcdfNormalizer = field(default_factory=EcdfNormalizer)
    n_train: int = 0

    def _matrix(self, features: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        matrix = features[self.feature_columns].to_numpy(dtype=float)
        valid = ~np.isnan(matrix).any(axis=1)
        return matrix, valid

    def fit(self, train_features: pd.DataFrame, candidate_columns=config.DETECTOR_FEATURES) -> "UnsupervisedDetector":
        # Use only columns that are populated in the training data (e.g. relative_return is absent without a benchmark).
        self.feature_columns = [c for c in candidate_columns if c in train_features.columns and train_features[c].notna().mean() > 0.9]
        matrix, valid = self._matrix(train_features)
        x_train = matrix[valid]
        if len(x_train) < config.MIN_TRAIN_BARS // 2:
            raise InsufficientTrainingData(f"{self.kind} needs at least {config.MIN_TRAIN_BARS // 2} complete training rows; got {len(x_train)}.")
        self.scaler = RobustScaler().fit(x_train)
        scaled = self.scaler.transform(x_train)
        if self.kind == "isolation_forest":
            self.model = IsolationForest(**config.ISOLATION_FOREST_PARAMS).fit(scaled)
            raw_train = -self.model.score_samples(scaled)
        elif self.kind == "lof":
            self.model = LocalOutlierFactor(**config.LOF_PARAMS).fit(scaled)
            raw_train = -self.model.negative_outlier_factor_
        else:
            raise ValueError(f"Unknown detector kind {self.kind}")
        self.normalizer.fit(raw_train)
        self.n_train = int(len(x_train))
        return self

    def raw_scores(self, features: pd.DataFrame) -> np.ndarray:
        matrix, valid = self._matrix(features)
        raw = np.full(len(matrix), np.nan)
        if valid.any():
            scaled = self.scaler.transform(matrix[valid])
            raw[valid] = -self.model.score_samples(scaled)
        return raw

    def score(self, features: pd.DataFrame) -> np.ndarray:
        return self.normalizer.transform(self.raw_scores(features))

    def metadata(self) -> dict:
        params = config.ISOLATION_FOREST_PARAMS if self.kind == "isolation_forest" else config.LOF_PARAMS
        return {"model": self.kind, "features": self.feature_columns, "n_train": self.n_train, "parameters": {k: v for k, v in params.items()}, "score_normalisation": f"training-ECDF, floor percentile {self.normalizer.floor}"}
