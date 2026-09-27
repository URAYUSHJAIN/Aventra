"""Capability-based feature sets and their versions.

The set is chosen from what the instrument's data actually provides; features that need missing fields are
never used. The `ohlcv` set is exactly the v0.1 equity configuration (preserved behaviour). Weights are equal
and heuristic (not validated) — see docs/05_ML_PIPELINE.md.
"""
from __future__ import annotations

import hashlib
import json

from ml import config

ROUND_THE_CLOCK = {"24/7", "24/5"}   # mirrors ml.data.calendars (no import: keeps features free of data-layer deps)

FEATURE_SETS: dict[str, dict] = {
    "ohlcv": {
        "fingerprint": dict(config.FINGERPRINT_WEIGHTS),
        "statistical": tuple(config.STATISTICAL_FEATURES),
        "detector": tuple(config.DETECTOR_FEATURES),
    },
    "ohlcv_continuous": {   # OHLCV on round-the-clock markets (e.g. Binance): a daily open equals the previous close, so no opening gap
        "fingerprint": {k: v for k, v in config.FINGERPRINT_WEIGHTS.items() if k != "gap_pct"},
        "statistical": tuple(config.STATISTICAL_FEATURES),
        "detector": tuple(f for f in config.DETECTOR_FEATURES if f != "gap_pct"),
    },
    "close_volume": {   # e.g. CoinGecko daily close + volume, no OHLC
        "fingerprint": {"return_1": 1.0, "log_volume": 1.0, "volatility_20": 1.0, "drawdown": 1.0, "relative_return": 1.0},
        "statistical": ("return_1", "log_volume"),
        "detector": ("return_1", "log_return", "return_5", "volatility_20", "volume_ratio", "ma20_distance", "rsi_14", "drawdown", "relative_return"),
    },
    "close": {          # NAV, FX reference rates, commodity spot, indices without volume
        "fingerprint": {"return_1": 1.0, "volatility_20": 1.0, "drawdown": 1.0, "ma20_distance": 1.0, "relative_return": 1.0},
        "statistical": ("return_1", "ma20_distance"),
        "detector": ("return_1", "log_return", "return_5", "volatility_20", "ma20_distance", "rsi_14", "drawdown", "relative_return"),
    },
    "yield": {          # interest rates / yields (basis points)
        "fingerprint": {"change_bp": 1.0, "volatility_bp_20": 1.0, "level_distance_bp": 1.0},
        "statistical": ("change_bp", "level_distance_bp"),
        "detector": ("change_bp", "change_5_bp", "volatility_bp_20", "level_distance_bp"),
    },
}


def select_set(profile: dict) -> str:
    if profile.get("value_kind") == "yield":
        return "yield"
    if profile.get("has_ohlc") and profile.get("has_volume"):
        return "ohlcv_continuous" if profile.get("calendar") in ROUND_THE_CLOCK else "ohlcv"
    if profile.get("has_volume"):
        return "close_volume"
    return "close"


def version(name: str) -> str:
    spec = {"set": FEATURE_SETS[name], "window": config.ROLLING_WINDOW, "rsi": config.RSI_WINDOW}
    return f"{name}-v1-{hashlib.sha1(json.dumps(spec, sort_keys=True, default=list).encode()).hexdigest()[:8]}"


def fingerprint_version() -> str:
    spec = {"window": config.FINGERPRINT_WINDOW, "min": config.FINGERPRINT_MIN_HISTORY, "guard": config.FINGERPRINT_GUARD_Z,
            "floor": config.Z_SCORE_FLOOR, "cap": config.Z_SCORE_CAP}
    return f"medmad-v1-{hashlib.sha1(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:8]}"


def thresholds_version() -> str:
    spec = {"ensemble": config.ENSEMBLE_WEIGHTS, "threshold": config.ANOMALY_THRESHOLD, "severity": config.SEVERITY_BANDS, "risk": config.RISK_WEIGHTS,
            "correlation": config.CORRELATION_WEIGHTS}
    return f"heuristic-v1-{hashlib.sha1(json.dumps(spec, sort_keys=True, default=list).encode()).hexdigest()[:8]}"
