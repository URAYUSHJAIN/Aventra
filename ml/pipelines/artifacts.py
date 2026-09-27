"""Versioned model artefacts (ML Pipeline §59): joblib binary + JSON metadata under artifacts/models/<symbol>/."""
from __future__ import annotations

import hashlib
import json
import logging

import joblib
import pandas as pd

from ml import config
from ml.data.store import now_iso

logger = logging.getLogger(__name__)


def _paths(symbol: str, kind: str):
    base = config.ARTIFACT_DIR / "models" / symbol
    return base / f"{kind}.joblib", base / f"{kind}.json"


def training_data_hash(train: pd.DataFrame, columns: list[str]) -> str:
    """Identifies the exact training matrix, so an artefact is reused only for identical data."""
    return "sha1:" + hashlib.sha1(train[columns].to_numpy(dtype=float).tobytes()).hexdigest()[:16]


def save_detector(symbol: str, detector, trained_through: str, data_source: str, data_hash: str) -> dict:
    binary, meta_path = _paths(symbol, detector.kind)
    binary.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(detector, binary)
    metadata = {
        "model_name": detector.kind, "model_version": f"{config.PIPELINE_VERSION}+{trained_through}", "symbol": symbol,
        "training_date": now_iso(), "trained_through": trained_through, "dataset_version": f"{data_source}/{data_hash}",
        "training_data_hash": data_hash, "random_seed": config.RANDOM_SEED, **detector.metadata(),
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def load_detector(symbol: str, kind: str, must_end_before: str, feature_columns: list[str], data_hash: str):
    """Return (detector, metadata) if a saved artefact was trained strictly before `must_end_before` on the
    same features and identical training data; otherwise (None, None). Prevents using a model that saw the
    scored period or was trained on different data."""
    binary, meta_path = _paths(symbol, kind)
    if not (binary.is_file() and meta_path.is_file()):
        return None, None
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        if (pd.Timestamp(metadata["trained_through"]) >= pd.Timestamp(must_end_before) or metadata["features"] != feature_columns
                or metadata.get("training_data_hash") != data_hash):
            return None, None
        return joblib.load(binary), metadata
    except Exception:
        logger.warning("Could not load artefact %s; refitting", binary, exc_info=True)
        return None, None
