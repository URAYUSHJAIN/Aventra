"""Transparent behavioural-risk score (ML Pipeline §27–28, with one documented refinement).

risk = 100 × [ w_a·anomaly + w_f·fingerprint
               + anomaly × (w_s·sentiment + w_c·correlation + w_t·temporal + w_k·confidence) ]

  anomaly      ensemble anomaly score of the bar                          (0–1)
  fingerprint  behavioural fingerprint deviation score                     (0–1)
  sentiment    |FinBERT sentiment score| of the best-correlated news item  (0–1)
  correlation  best cross-source correlation score                         (0–1)
  temporal     temporal proximity of the best-correlated news item         (0–1)
  confidence   detector agreement (1 − spread of the detector scores)      (0–1)

Refinement (anomaly gate): ML Pipeline §27 sums all six terms directly. Tested on
real NSE data, that gave ordinary sessions (anomaly ≈ 0) a risk near 48 simply
because news existed that day and the detectors "agreed" the session was normal.
The context and confidence terms therefore scale with the anomaly score: context
strengthens a behavioural deviation, but cannot create risk on its own.

Weights are config.RISK_WEIGHTS (defaults, not calibrated). The score is still a sum
of per-component contributions (reported below), so the decomposition is exact.
When news context is unavailable the news-based components are unavailable (0
contribution) and the basis says so — they are never estimated.
Risk is a contextual signal, not a prediction of future prices or financial advice.
"""
from __future__ import annotations

import math

from ml import config

DESCRIPTIONS = {
    "anomaly": "Ensemble anomaly score of the bar",
    "fingerprint": "Deviation from the asset's behavioural fingerprint",
    "sentiment": "Strength of financial-news sentiment of the best-aligned article",
    "correlation": "Cross-source correlation score of the best-aligned article",
    "temporal": "Temporal proximity of the best-aligned article to the session",
    "confidence": "Agreement between anomaly detectors",
}


UNGATED = {"anomaly", "fingerprint"}


def _safe(value) -> float | None:
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(value) else min(max(value, 0.0), 1.0)


def compute_risk(anomaly_score, fingerprint_score, model_agreement, correlation: dict | None, news_status: str) -> dict:
    best = correlation["matches"][0] if correlation and correlation.get("matches") else None
    news_context = best is not None
    values = {
        "anomaly": _safe(anomaly_score),
        "fingerprint": _safe(fingerprint_score),
        "sentiment": _safe(best["components"]["sentiment_strength"]) if best and best["sentiment_available"] else (0.0 if news_status == "ok" else None),
        "correlation": _safe(best["correlation_score"]) if best else (0.0 if news_status == "ok" else None),
        "temporal": _safe(best["components"]["temporal_proximity"]) if best else (0.0 if news_status == "ok" else None),
        "confidence": _safe(model_agreement),
    }
    gate = values["anomaly"] or 0.0
    components, total = [], 0.0
    for name, weight in config.RISK_WEIGHTS.items():
        value = values[name]
        factor = 1.0 if name in UNGATED else gate
        contribution = 0.0 if value is None else weight * factor * value * 100
        total += contribution
        components.append({
            "name": name, "description": DESCRIPTIONS[name], "value": None if value is None else round(value, 4),
            "weight": weight, "gate": round(factor, 4), "contribution": round(contribution, 2), "available": value is not None,
        })
    if news_context:
        basis = "market_and_news"
    elif news_status == "ok":
        basis = "market_only_no_aligned_news"
    else:
        basis = "market_only_news_unavailable"
    score = round(total, 1)
    return {
        "score": score, "level": config.risk_level_for(score), "basis": basis, "components": components,
        "method": "weighted sum with context terms gated by the anomaly score (ML Pipeline §27 + documented gate); weights are uncalibrated defaults",
        "disclaimer": "Analytical signal only; not a price prediction or financial advice.",
    }
