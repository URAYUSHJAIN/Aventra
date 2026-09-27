"""EXPERIMENTAL — LSTM autoencoder detector (Final Plan §10 model C).

Used only in offline evaluation (ml/evaluation); not part of the production ensemble
until it beats the baselines on validation data (Final Plan §29: deep models after
baselines). The window ending at bar t is reconstructed; the reconstruction error
of the last step is the raw anomaly score, normalised with the training-error ECDF.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

from ml import config
from ml.anomaly.detectors import EcdfNormalizer

SEQ_LEN = 20
HIDDEN = 16
EPOCHS = 30
BATCH = 64
LR = 1e-3


def _windows(matrix: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """All windows of SEQ_LEN consecutive complete rows; returns (windows, end_index)."""
    ends = [t for t in range(SEQ_LEN - 1, len(matrix)) if valid[t - SEQ_LEN + 1:t + 1].all()]
    if not ends:
        return np.empty((0, SEQ_LEN, matrix.shape[1])), np.array([], dtype=int)
    return np.stack([matrix[t - SEQ_LEN + 1:t + 1] for t in ends]), np.array(ends)


class LstmAutoencoderDetector:
    kind = "lstm_autoencoder"

    def __init__(self, seed: int = config.RANDOM_SEED):
        self.seed = seed
        self.feature_columns: list[str] = []
        self.normalizer = EcdfNormalizer()

    def _prepare(self, features: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        matrix = features[self.feature_columns].to_numpy(dtype=float)
        valid = ~np.isnan(matrix).any(axis=1)
        scaled = np.zeros_like(matrix)
        scaled[valid] = np.clip(self.scaler.transform(matrix[valid]), -10, 10)
        return scaled, valid

    def fit(self, train: pd.DataFrame, candidate_columns=config.DETECTOR_FEATURES) -> "LstmAutoencoderDetector":
        import torch
        from torch import nn

        torch.manual_seed(self.seed)
        np.random.seed(self.seed)
        self.feature_columns = [c for c in candidate_columns if c in train.columns and train[c].notna().mean() > 0.9]
        raw = train[self.feature_columns].to_numpy(dtype=float)
        self.scaler = RobustScaler().fit(raw[~np.isnan(raw).any(axis=1)])
        scaled, valid = self._prepare(train)
        windows, _ = _windows(scaled, valid)
        n_features = len(self.feature_columns)

        class Model(nn.Module):
            def __init__(self):
                super().__init__()
                self.encoder = nn.LSTM(n_features, HIDDEN, batch_first=True)
                self.decoder = nn.LSTM(HIDDEN, HIDDEN, batch_first=True)
                self.output = nn.Linear(HIDDEN, n_features)

            def forward(self, x):
                _, (h, _) = self.encoder(x)
                repeated = h[-1].unsqueeze(1).repeat(1, x.shape[1], 1)
                decoded, _ = self.decoder(repeated)
                return self.output(decoded)

        self.model = Model()
        optimiser = torch.optim.Adam(self.model.parameters(), lr=LR)
        data = torch.tensor(windows, dtype=torch.float32)
        generator = torch.Generator().manual_seed(self.seed)
        self.model.train()
        for _ in range(EPOCHS):
            for batch in torch.split(data[torch.randperm(len(data), generator=generator)], BATCH):
                optimiser.zero_grad()
                loss = nn.functional.mse_loss(self.model(batch), batch)
                loss.backward()
                optimiser.step()
        self.model.eval()
        self.normalizer.fit(self._raw(train))
        self.n_train = int(len(windows))
        return self

    def _raw(self, features: pd.DataFrame) -> np.ndarray:
        import torch
        scaled, valid = self._prepare(features)
        windows, ends = _windows(scaled, valid)
        raw = np.full(len(features), np.nan)
        if len(windows):
            with torch.no_grad():
                x = torch.tensor(windows, dtype=torch.float32)
                errors = ((self.model(x) - x) ** 2)[:, -1, :].mean(dim=1).numpy()
            raw[ends] = errors
        return raw

    def score(self, features: pd.DataFrame) -> np.ndarray:
        return self.normalizer.transform(self._raw(features))
