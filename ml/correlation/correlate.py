"""Cross-source event correlation (ML Pipeline §23–24, Final Plan §12).

A market anomaly on trading date D is associated with news about the same asset
published inside [session open − LOOKBACK, session close + LOOKAHEAD]. Each
candidate gets

  correlation_score = 0.30·temporal_proximity + 0.25·asset_match
                    + 0.20·sentiment_strength + 0.25·anomaly_strength

(config.CORRELATION_WEIGHTS — an engineering starting point, not a validated
formula). A high score means the signals are temporally aligned and about the same
asset; it does NOT establish that the news caused the movement.
"""
from __future__ import annotations

import pandas as pd

from ml import config
from ml.correlation import semantic
from ml.data.sessions import iso, session_bounds, to_utc
from ml.news.events import classify_event


def _relation(published: pd.Timestamp, open_utc: pd.Timestamp, close_utc: pd.Timestamp) -> tuple[str, float, float]:
    """(relation label, signed hours relative to the session, temporal proximity in [0, 1])."""
    if published < open_utc:
        hours = (open_utc - published).total_seconds() / 3600
        return "published_before_session", -hours, max(0.0, 1 - hours / config.CORRELATION_LOOKBACK_HOURS)
    if published > close_utc:
        hours = (published - close_utc).total_seconds() / 3600
        return "published_after_session_close", hours, max(0.0, 1 - hours / config.CORRELATION_LOOKAHEAD_HOURS)
    return "published_during_session", 0.0, 1.0


def event_description(asset_name: str, contributing: list[dict]) -> str:
    parts = [item["label"].lower() + (" higher" if item["direction"] == "above" else " lower") for item in contributing[:3]]
    return f"Unusual trading behaviour in {asset_name}: " + (", ".join(parts) if parts else "deviation from normal behaviour")


def correlate(trading_date, anomaly_score: float, contributing: list[dict], news_items: list[dict], symbol: str, asset_name: str) -> dict:
    open_utc, close_utc = session_bounds(trading_date)
    start = open_utc - pd.Timedelta(hours=config.CORRELATION_LOOKBACK_HOURS)
    end = close_utc + pd.Timedelta(hours=config.CORRELATION_LOOKAHEAD_HOURS)
    window = {"start": iso(start), "end": iso(end), "session_open": iso(open_utc), "session_close": iso(close_utc)}

    candidates = []
    for item in news_items:
        link = next((l for l in item.get("links", []) if l["symbol"] == symbol), None)
        if link is None or link["entity_match_confidence"] < config.ENTITY_MIN_CONFIDENCE:
            continue
        published = to_utc(item["published_at"])
        if start <= published <= end:
            candidates.append((item, link, published))
    if not candidates:
        return {"status": "no_aligned_news", "window": window, "best_score": 0.0, "matches": []}

    description = event_description(asset_name, contributing)
    sims = semantic.similarities(description, [item["headline"] for item, _, _ in candidates])
    w = config.CORRELATION_WEIGHTS
    matches = []
    for index, (item, link, published) in enumerate(candidates):
        relation, hours, proximity = _relation(published, open_utc, close_utc)
        sentiment = item.get("sentiment")
        strength = abs(float(sentiment["sentiment_score"])) if sentiment else 0.0
        components = {
            "temporal_proximity": round(proximity, 4), "asset_match": round(float(link["entity_match_confidence"]), 4),
            "sentiment_strength": round(strength, 4), "anomaly_strength": round(float(anomaly_score), 4),
        }
        score = sum(w[name] * value for name, value in components.items())
        matches.append({
            "news_id": item["news_id"], "headline": item["headline"], "source": item.get("source"), "url": item.get("url"),
            "published_at": item["published_at"], "sentiment": sentiment, "entity": {"confidence": link["entity_match_confidence"], "method": link["mapping_method"]},
            "category": classify_event(item["headline"] + " " + (item.get("summary") or "")),
            "relation": relation, "hours_from_session": round(hours, 2), "components": components, "weights": w,
            "correlation_score": round(score, 4), "semantic_relevance": sims[index] if sims is not None else None,
            "sentiment_available": sentiment is not None,
        })
    matches.sort(key=lambda m: (m["correlation_score"], m["semantic_relevance"] or 0), reverse=True)
    matches = matches[: config.MAX_NEWS_PER_EVENT]
    return {
        "status": "aligned_news_found", "window": window, "best_score": matches[0]["correlation_score"], "matches": matches,
        "event_description": description, "semantic_model": semantic.model_info(),
        "interpretation": "Scores measure temporal alignment and asset match between signals; they do not establish causation.",
    }
