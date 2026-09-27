"""Central configuration for the Aventra pipeline.

Every threshold and weight below is an engineering DEFAULT chosen to make the
pipeline runnable. None of them is a validated scientific value; calibration
must use validation data only (see docs/05_ML_PIPELINE.md). Values can be
overridden through environment variables where noted.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("AVENTRA_DATA_DIR", PROJECT_ROOT / "data"))
DEMO_DIR = DATA_DIR / "demo"
REFERENCE_DIR = DATA_DIR / "reference"
ARTIFACT_DIR = Path(os.getenv("AVENTRA_ARTIFACT_DIR", PROJECT_ROOT / "artifacts"))
EXPERIMENT_DIR = PROJECT_ROOT / "experiments" / "results"
DB_PATH = Path(os.getenv("AVENTRA_DB_PATH", DATA_DIR / "aventra.sqlite3"))

PIPELINE_VERSION = "0.1.0"
RANDOM_SEED = 42

# --- Market / time -----------------------------------------------------------
MARKET_TIMEZONE = "Asia/Kolkata"
SESSION_OPEN = (9, 15)    # NSE regular session, local time
SESSION_CLOSE = (15, 30)
HISTORY_RANGE = os.getenv("AVENTRA_HISTORY_RANGE", "5y")   # daily bars used for analytics
BENCHMARK_SYMBOL = "^NSEI"                                  # NIFTY 50
PROVIDER_TIMEOUT_SECONDS = 12
QUOTE_CACHE_SECONDS = 60
HISTORY_CACHE_SECONDS = 6 * 60 * 60
NEWS_CACHE_SECONDS = 30 * 60
INTELLIGENCE_CACHE_SECONDS = 15 * 60

# --- Features ----------------------------------------------------------------
ROLLING_WINDOW = 20          # bars; rolling mean/std use prior bars only
RSI_WINDOW = 14

# --- Behavioural fingerprint --------------------------------------------------
FINGERPRINT_WINDOW = 120     # prior bars forming the baseline
FINGERPRINT_MIN_HISTORY = 60 # below this -> status "insufficient_history"
FINGERPRINT_GUARD_Z = 4.0    # observations beyond this robust z enter the baseline clipped (guarded update)
Z_SCORE_FLOOR = 2.0          # |z| at or below -> deviation score 0
Z_SCORE_CAP = 6.0            # |z| at or above -> deviation score 1
FINGERPRINT_WEIGHTS = {      # equal weights by default; not validated
    "return_1": 1.0,
    "log_volume": 1.0,
    "volatility_20": 1.0,
    "range_pct": 1.0,
    "gap_pct": 1.0,
    "relative_return": 1.0,
}
FINGERPRINT_LEVELS = ((0.75, "high_deviation"), (0.50, "elevated_deviation"), (0.25, "mild_deviation"), (0.0, "normal"))
STATISTICAL_FEATURES = ("return_1", "log_volume", "range_pct")

# --- Anomaly detection ------------------------------------------------------------
SCORING_WINDOW = 250         # most recent bars that are scored; models fit only on bars before it
MIN_TRAIN_BARS = 200
ISOLATION_FOREST_PARAMS = {"n_estimators": 200, "contamination": "auto", "random_state": RANDOM_SEED}
LOF_PARAMS = {"n_neighbors": 20, "novelty": True}
ML_SCORE_PERCENTILE_FLOOR = 0.90   # training-score percentile below which the ML score is 0
ENSEMBLE_WEIGHTS = {"statistical": 0.35, "fingerprint": 0.35, "isolation_forest": 0.30}
ANOMALY_THRESHOLD = float(os.getenv("AVENTRA_ANOMALY_THRESHOLD", "0.65"))
SEVERITY_BANDS = ((0.85, "CRITICAL"), (0.65, "HIGH"), (0.40, "MEDIUM"), (0.0, "LOW"))
DETECTOR_FEATURES = (
    "return_1", "log_return", "return_5", "volatility_20", "volume_ratio",
    "gap_pct", "range_pct", "ma20_distance", "rsi_14", "relative_return",
)

# --- News / correlation -------------------------------------------------------------
ENTITY_MIN_CONFIDENCE = 0.6          # news below this is never linked to an asset
CORRELATION_LOOKBACK_HOURS = 24      # news published up to this long before the session opens
CORRELATION_LOOKAHEAD_HOURS = 12     # ... or this long after the session closes
CORRELATION_WEIGHTS = {"temporal_proximity": 0.30, "asset_match": 0.25, "sentiment_strength": 0.20, "anomaly_strength": 0.25}
SEMANTIC_MODEL = os.getenv("AVENTRA_SEMANTIC_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
MAX_NEWS_PER_EVENT = 5

# --- Risk ---------------------------------------------------------------------------
RISK_WEIGHTS = {
    "anomaly": 0.25,
    "fingerprint": 0.20,
    "sentiment": 0.15,
    "correlation": 0.20,
    "temporal": 0.10,
    "confidence": 0.10,
}
RISK_LEVELS = ((75, "HIGH"), (50, "ELEVATED"), (25, "MODERATE"), (0, "LOW"))


def synthetic_test_data_enabled() -> bool:
    """The synthetic TEST:DEMO instrument (data/demo) exists only for the automated test-suite.
    It is enabled solely by AVENTRA_ENABLE_SYNTHETIC_TEST_DATA=1 and must never be set in user-facing deployments."""
    return os.getenv("AVENTRA_ENABLE_SYNTHETIC_TEST_DATA", "").strip() == "1"


def severity_for(score: float) -> str:
    return next(label for floor, label in SEVERITY_BANDS if score >= floor)


def risk_level_for(score: float) -> str:
    return next(label for floor, label in RISK_LEVELS if score >= floor)
