"""Evidence chain and explanation (ML Pipeline §29–30, Final Plan §17).

Every item points back to the signal that produced it (market provider, detector,
news source, FinBERT, correlation, risk model). Wording is associative, never causal.
"""
from __future__ import annotations

from ml.data.sessions import iso
from ml.temporal.analysis import build_timeline, session_relation_text

FEATURE_TYPES = {"return_1": "price", "gap_pct": "price", "relative_return": "price", "log_volume": "volume", "volatility_20": "volatility", "range_pct": "volatility"}


def build_evidence(assessment: dict, market_source: str, change_points: list[str]) -> list[dict]:
    anomaly, correlation, risk = assessment["anomaly"], assessment["correlation"], assessment["risk"]
    session_open, session_close = correlation["window"]["session_open"], correlation["window"]["session_close"]
    items: list[dict] = []
    for feature in anomaly["contributing_features"]:
        items.append({"timestamp": session_close, "type": FEATURE_TYPES.get(feature["feature"], "market"), "signal": feature["feature"],
                      "description": feature["explanation"], "value": feature["robust_z"], "source": f"market:{market_source}"})
    scores = anomaly["scores"]
    detector_text = ", ".join(f"{name.replace('_', ' ')} {value:.2f}" for name, value in scores.items() if value is not None)
    items.append({"timestamp": session_close, "type": "anomaly", "signal": "anomaly_ensemble",
                  "description": f"Ensemble anomaly score {anomaly['anomaly_score']:.2f} ({anomaly['severity']}); detectors: {detector_text}; agreement {anomaly['model_agreement']:.2f}.",
                  "value": anomaly["anomaly_score"], "source": "aventra:anomaly_ensemble"})
    for match in correlation.get("matches", []):
        items.append({"timestamp": match["published_at"], "type": "news", "signal": "news_article",
                      "description": f"{match['headline']} — {match.get('source') or 'unknown source'} ({session_relation_text(match['hours_from_session'], match['relation'])}; category: {match['category']['category']}).",
                      "value": match["entity"]["confidence"], "source": f"news:{match.get('source') or 'unknown'}", "url": match.get("url")})
        if match["sentiment"]:
            s = match["sentiment"]
            items.append({"timestamp": match["published_at"], "type": "sentiment", "signal": "finbert",
                          "description": f"FinBERT classified the headline as {s['label']} (score {s['sentiment_score']:+.2f}, confidence {s['confidence']:.2f}).",
                          "value": s["sentiment_score"], "source": "model:finbert"})
        items.append({"timestamp": match["published_at"], "type": "correlation", "signal": "cross_source_correlation",
                      "description": f"Temporally aligned with the market anomaly: correlation score {match['correlation_score']:.2f} (entity match {match['entity']['method']}).",
                      "value": match["correlation_score"], "source": "aventra:correlation"})
    nearby = [cp for cp in change_points if cp == assessment["trading_date"]]
    for cp in nearby:
        items.append({"timestamp": session_open, "type": "regime", "signal": "change_point",
                      "description": f"Retrospective change-point analysis (PELT) places a behaviour regime boundary on {cp}. Retrospective context only.",
                      "value": None, "source": "model:ruptures_pelt"})
    items.append({"timestamp": session_close, "type": "risk", "signal": "risk_score",
                  "description": f"Risk signal {risk['score']:.0f}/100 ({risk['level']}), basis: {risk['basis'].replace('_', ' ')}.",
                  "value": risk["score"], "source": "aventra:risk_model"})
    return build_timeline(items)


def build_explanation(assessment: dict, asset_name: str) -> dict:
    anomaly, correlation, risk = assessment["anomaly"], assessment["correlation"], assessment["risk"]
    features = anomaly["contributing_features"]
    what = (f"{asset_name} showed behaviour that deviated from its own historical baseline on {assessment['trading_date']}."
            if features else f"No behavioural dimension of {asset_name} deviated beyond 2 robust standard deviations on {assessment['trading_date']}.")
    matches = correlation.get("matches", [])
    if matches:
        best = matches[0]
        news = f"{len(matches)} article(s) about the asset were published inside the analysis window; the best-aligned was “{best['headline']}”."
        timing = f"The best-aligned article was {session_relation_text(best['hours_from_session'], best['relation'])}."
    elif correlation["status"] == "no_aligned_news":
        news, timing = "No asset-linked news was found inside the analysis window.", "Not applicable."
    else:
        news, timing = "News context unavailable for this assessment.", "Not applicable."
    top = sorted(risk["components"], key=lambda c: c["contribution"], reverse=True)[:3]
    return {
        "what": what,
        "when": f"Trading session {assessment['trading_date']} ({correlation['window']['session_open']} – {correlation['window']['session_close']} UTC).",
        "how_unusual": f"Ensemble anomaly score {anomaly['anomaly_score']:.2f} ({anomaly['severity']}); fingerprint deviation {assessment['fingerprint_score']:.2f}." if assessment.get("fingerprint_score") is not None else f"Ensemble anomaly score {anomaly['anomaly_score']:.2f} ({anomaly['severity']}).",
        "signals": [f["explanation"] for f in features] or ["No individual dimension exceeded the reporting threshold."],
        "news": news,
        "timing": timing,
        "why": f"Risk {risk['score']:.0f}/100 ({risk['level']}); largest contributions: " + ", ".join(f"{c['name']} {c['contribution']:.1f}" for c in top) + ".",
        "caveat": "Signals are temporally aligned; this does not show that any article caused the price movement.",
    }


__all__ = ["build_evidence", "build_explanation", "iso"]
