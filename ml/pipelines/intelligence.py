"""End-to-end intelligence pipeline for one asset (ML Pipeline §54).

Market data → validation/cleaning → temporal alignment → features → behavioural
fingerprint → anomaly detection → news + FinBERT → cross-source correlation →
temporal analysis → risk → evidence chain. Returns one JSON-serialisable result
that the Flask API serves and the React dashboard renders.
"""
from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ml import config
from ml.anomaly.changepoint import detect_change_points
from ml.anomaly.detectors import InsufficientTrainingData, UnsupervisedDetector
from ml.anomaly.ensemble import combine
from ml.anomaly.explain import LABELS, contributing_features
from ml.anomaly.statistical import statistical_scores
from ml.correlation.correlate import correlate
from ml.data import store
from ml.data.assets import benchmark, get_asset
from ml.data.market_providers import ProviderError, YahooChartProvider, provider_for
from ml.data.sessions import align_to_session, is_session_in_progress, iso, session_bounds
from ml.data.validation import validate_ohlcv
from ml.evidence.chain import build_evidence, build_explanation
from ml.features.engineering import FEATURE_DEFINITIONS, compute_features
from ml.fingerprint.baseline import compute_fingerprint, fingerprint_level
from ml.news.ingest import ingest_news
from ml.pipelines import artifacts
from ml.risk.scoring import compute_risk
from ml.temporal.analysis import lead_lag

logger = logging.getLogger(__name__)
DISCLAIMER = "Aventra provides analytical signals and evidence, not financial advice or guaranteed predictions."


class UnknownAsset(LookupError):
    pass


class InsufficientHistory(ValueError):
    pass


def _num(value, digits: int = 6):
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(value) or math.isinf(value) else round(value, digits)


# --- stage 1: market data with cached fallback ------------------------------------------------
def load_market(symbol: str, provider=None) -> tuple[pd.DataFrame, dict, dict]:
    provider = provider or provider_for(symbol)
    source = {"provider": provider.name, "is_demo": provider.is_demo, "stale": False, "notes": []}
    try:
        raw = provider.get_history(symbol)
        source["fetched_at"] = store.now_iso()
        if not provider.is_demo:
            store.upsert_prices(raw)
    except ProviderError as error:
        if error.kind == "not_found" or provider.is_demo:
            raise
        cached, fetched_at = store.load_prices(symbol)
        if cached.empty:
            raise
        logger.warning("Provider failed for %s; using stored prices from %s", symbol, fetched_at)
        raw, source["stale"], source["fetched_at"] = cached, True, fetched_at
        source["notes"].append("Live provider unavailable; using previously stored prices.")
    bars, report = validate_ohlcv(raw, symbol)
    last_date = bars["timestamp"].iloc[-1]
    if not provider.is_demo and is_session_in_progress(pd.Timestamp(last_date).tz_convert(config.MARKET_TIMEZONE).date()):
        bars = bars.iloc[:-1]
        source["notes"].append("The in-progress trading session was excluded: daily analytics use completed sessions only.")
    return bars.reset_index(drop=True), source, report


def load_benchmark(is_demo: bool) -> tuple[pd.DataFrame | None, dict | None]:
    if is_demo:
        return None, None
    info = benchmark()
    try:
        raw = YahooChartProvider().get_history(info["provider_symbol"])
        bars, _ = validate_ohlcv(raw, info["symbol"])
        return bars, {"symbol": info["symbol"], "name": info["name"], "status": "ok"}
    except (ProviderError, ValueError) as error:
        logger.warning("Benchmark unavailable: %s", error)
        return None, {"symbol": info["symbol"], "name": info["name"], "status": "unavailable"}


# --- stage 5: anomaly detection -----------------------------------------------------------------
def fit_or_load_detector(symbol: str, train: pd.DataFrame, window_start_date: str, source_name: str) -> tuple[UnsupervisedDetector | None, dict]:
    probe = UnsupervisedDetector("isolation_forest")
    columns = [c for c in config.DETECTOR_FEATURES if c in train.columns and train[c].notna().mean() > 0.9]
    data_hash = artifacts.training_data_hash(train, columns)
    detector, metadata = artifacts.load_detector(symbol, "isolation_forest", window_start_date, columns, data_hash)
    if detector is not None:
        return detector, {**metadata, "status": "ok", "loaded_from_artifact": True}
    try:
        detector = probe.fit(train)
    except InsufficientTrainingData as error:
        return None, {"model": "isolation_forest", "status": "insufficient_history", "reason": str(error)}
    trained_through = str(train["trading_date"].iloc[-1].date())
    metadata = artifacts.save_detector(symbol, detector, trained_through, source_name, data_hash)
    return detector, {**metadata, "status": "ok", "loaded_from_artifact": False}


def _scoring_window(n: int) -> int:
    """Index where scoring starts; detectors are fitted only on rows before it."""
    return max(n - config.SCORING_WINDOW, min(config.MIN_TRAIN_BARS + config.ROLLING_WINDOW, n))


# --- per-bar assessment -------------------------------------------------------------------------------
def assess_bar(i: int, symbol: str, asset, feats, fp, stat, ens, dims, news_items, news_status, market_source, change_points) -> dict:
    row_fp = fp.iloc[i].to_dict()
    trading_date = feats["trading_date"].iloc[i]
    date_str = trading_date.strftime("%Y-%m-%d")
    contributing = contributing_features(row_fp, dims, feats.iloc[i])
    anomaly = {
        "anomaly_id": f"AN-{symbol}-{trading_date.strftime('%Y%m%d')}", "trading_date": date_str,
        "timestamp": iso(session_bounds(trading_date)[0]), "anomaly_score": _num(ens["anomaly_score"].iloc[i], 4) or 0.0,
        "severity": ens["severity"].iloc[i], "is_anomaly": bool(ens["is_anomaly"].iloc[i]),
        "scores": {"statistical": _num(stat["statistical_score"].iloc[i], 4), "fingerprint": _num(fp["fingerprint_score"].iloc[i], 4), "isolation_forest": _num(ens["_if"].iloc[i], 4)},
        "model_agreement": _num(ens["model_agreement"].iloc[i], 4) or 0.0, "contributing_features": contributing,
    }
    correlation = correlate(trading_date, anomaly["anomaly_score"], contributing, news_items, symbol, asset.name) if news_status != "unavailable" else {
        "status": "news_unavailable", "window": {**dict(zip(("session_open", "session_close"), map(iso, session_bounds(trading_date)))), "start": None, "end": None}, "best_score": 0.0, "matches": []}
    risk = compute_risk(anomaly["anomaly_score"], anomaly["scores"]["fingerprint"], anomaly["model_agreement"], correlation, "ok" if news_status != "unavailable" else "unavailable")
    assessment = {"event_id": f"EV-{symbol}-{trading_date.strftime('%Y%m%d')}", "trading_date": date_str, "anomaly": anomaly, "correlation": correlation,
                  "risk": risk, "fingerprint_score": anomaly["scores"]["fingerprint"], "window": {"start": correlation["window"]["start"], "end": correlation["window"]["end"]}}
    assessment["evidence"] = build_evidence(assessment, market_source, change_points)
    assessment["explanation"] = build_explanation(assessment, asset.name)
    anomaly["explanation"] = assessment["explanation"]["signals"]
    return assessment


def run_intelligence(symbol: str, persist: bool = True) -> dict:
    started = time.perf_counter()
    asset = get_asset(symbol)
    if asset is None:
        raise UnknownAsset(f"{symbol} is not in Aventra's analysed asset universe.")
    timings: dict[str, float] = {}

    def tick(stage: str, since: float) -> float:
        now = time.perf_counter()
        timings[stage] = round((now - since) * 1000, 1)
        logger.info("pipeline stage=%s symbol=%s status=ok duration_ms=%.1f", stage, symbol, timings[stage])
        return now

    t = time.perf_counter()
    bars, market_source, validation = load_market(symbol)
    bench, bench_info = load_benchmark(asset.is_demo)
    t = tick("market_data", t)
    feats = compute_features(bars, bench)
    t = tick("features", t)
    if len(feats) < config.FINGERPRINT_MIN_HISTORY + config.ROLLING_WINDOW:
        raise InsufficientHistory(f"{symbol} has {len(feats)} usable sessions; at least {config.FINGERPRINT_MIN_HISTORY + config.ROLLING_WINDOW} are required.")
    fp, fp_meta = compute_fingerprint(feats)
    t = tick("fingerprint", t)

    n = len(feats)
    start = _scoring_window(n)
    stat = statistical_scores(feats)
    window_start_date = str(feats["trading_date"].iloc[start].date())
    detector, detector_meta = fit_or_load_detector(symbol, feats.iloc[:start], window_start_date, market_source["provider"])
    if_scores = detector.score(feats) if detector is not None else np.full(n, np.nan)
    if_scores[:start] = np.nan   # in-sample scores are never reported
    components = pd.DataFrame({"statistical": stat["statistical_score"], "fingerprint": fp["fingerprint_score"], "isolation_forest": if_scores})
    ens = combine(components)
    ens["_if"] = if_scores
    change = detect_change_points(feats.iloc[start:])
    t = tick("anomaly_detection", t)

    news = ingest_news(symbol, asset)
    t = tick("news_and_sentiment", t)

    dims = fp_meta["dimensions"]
    flagged = [i for i in range(start, n) if bool(ens["is_anomaly"].iloc[i])]
    args = (symbol, asset, feats, fp, stat, ens, dims, news["items"], news["status"], market_source["provider"], change.get("change_points", []))
    events = [assess_bar(i, *args) for i in reversed(flagged)]
    current = assess_bar(n - 1, *args)
    t = tick("correlation_risk_evidence", t)

    trading_dates = list(feats["trading_date"])
    daily_sentiment: dict = {}
    for item in news["items"]:
        if item.get("sentiment"):
            aligned = align_to_session(item["published_at"], trading_dates)
            if aligned is not None:
                daily_sentiment.setdefault(aligned, []).append(item["sentiment"]["sentiment_score"])
    lead_lag_result = lead_lag(feats.set_index("trading_date")["return_1"], pd.Series({d: float(np.mean(v)) for d, v in daily_sentiment.items()}, dtype=float))

    last = feats.iloc[-1]
    fp_last = fp.iloc[-1]
    window_slice = slice(start, n)
    result = {
        "run_id": f"RUN-{symbol}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}",
        "symbol": symbol, "asset": asset.to_dict(), "generated_at": store.now_iso(), "pipeline_version": config.PIPELINE_VERSION,
        "data_source": {"market": market_source, "benchmark": bench_info, "news": {k: v for k, v in news.items() if k != "items"}},
        "validation": validation,
        "market": {
            "latest": {"trading_date": last["trading_date"].strftime("%Y-%m-%d"), "open": _num(last["open"], 4), "high": _num(last["high"], 4), "low": _num(last["low"], 4),
                       "close": _num(last["close"], 4), "volume": _num(last["volume"], 0), "return_1": _num(last["return_1"]), "volatility_20": _num(last["volatility_20"]),
                       "volume_ratio": _num(last["volume_ratio"], 4)},
            "series": [
                {"date": feats["trading_date"].iloc[i].strftime("%Y-%m-%d"), "open": _num(feats["open"].iloc[i], 4), "high": _num(feats["high"].iloc[i], 4), "low": _num(feats["low"].iloc[i], 4),
                 "close": _num(feats["close"].iloc[i], 4), "volume": _num(feats["volume"].iloc[i], 0), "anomaly_score": _num(ens["anomaly_score"].iloc[i], 4),
                 "is_anomaly": bool(ens["is_anomaly"].iloc[i]), "severity": ens["severity"].iloc[i]}
                for i in range(start, n)
            ],
        },
        "fingerprint": {
            "as_of": last["trading_date"].strftime("%Y-%m-%d"), "score": _num(fp_last["fingerprint_score"], 4), "level": fingerprint_level(fp_last["fingerprint_score"]),
            "status": fp_last["fingerprint_status"],
            "dimensions": [_dimension(dim, last, fp_last, fp_meta) for dim in dims],
            "series": {dim: _dimension_series(dim, feats, fp, window_slice) for dim in dims},
            "method": {"baseline": "rolling median / MAD of prior bars (robust z-score)", "window": config.FINGERPRINT_WINDOW, "min_history": config.FINGERPRINT_MIN_HISTORY,
                       "guarded_update_z": config.FINGERPRINT_GUARD_Z, "score_mapping": f"linear from |z|={config.Z_SCORE_FLOOR} (0) to |z|={config.Z_SCORE_CAP} (1)", "weights": fp_meta["weights"]},
        },
        "anomaly": {
            "current": current["anomaly"], "threshold": config.ANOMALY_THRESHOLD, "flagged_count": len(flagged),
            "window": {"start": window_start_date, "end": last["trading_date"].strftime("%Y-%m-%d"), "bars": n - start},
            "ensemble_weights": config.ENSEMBLE_WEIGHTS, "severity_bands": [{"min": floor, "label": label} for floor, label in config.SEVERITY_BANDS],
            "change_points": change,
        },
        "news": {"status": news["status"], "message": news.get("message"), "items": [_news_view(item, symbol) for item in news["items"][:40]],
                 "sentiment_summary": _sentiment_summary(news["items"])},
        "current_assessment": current,
        "events": events,
        "lead_lag": lead_lag_result,
        "models": {"isolation_forest": detector_meta, "finbert": {"model": "ProsusAI/finBERT", "status": news.get("sentiment_status")},
                   "semantic": next((e["correlation"].get("semantic_model") for e in [current, *events] if e["correlation"].get("semantic_model")), None)},
        "parameters": {"scoring_window": config.SCORING_WINDOW, "anomaly_threshold": config.ANOMALY_THRESHOLD, "correlation_weights": config.CORRELATION_WEIGHTS,
                       "risk_weights": config.RISK_WEIGHTS, "correlation_lookback_hours": config.CORRELATION_LOOKBACK_HOURS, "correlation_lookahead_hours": config.CORRELATION_LOOKAHEAD_HOURS,
                       "random_seed": config.RANDOM_SEED, "calibration_status": "uncalibrated defaults"},
        "feature_definitions": FEATURE_DEFINITIONS,
        "timings_ms": {**timings, "total": round((time.perf_counter() - started) * 1000, 1)},
        "disclaimer": DISCLAIMER,
    }
    if persist:
        store.save_run(result)
    return result


def _dimension(dim, last, fp_last, fp_meta) -> dict:
    to_display = (lambda v: math.expm1(v) if v is not None else None) if dim == "log_volume" else (lambda v: v)
    median, scale = _num(fp_last.get(f"median_{dim}")), _num(fp_last.get(f"scale_{dim}"))
    q = fp_meta["quantiles"].get(dim, {})
    return {
        "feature": dim, "label": LABELS.get(dim, dim), "unit": "shares" if dim == "log_volume" else "fraction",
        "value": _num(to_display(_num(last[dim]))), "baseline_median": _num(to_display(median)),
        "p05": _num(to_display(q.get("p05"))), "p95": _num(to_display(q.get("p95"))),
        "robust_z": _num(fp_last.get(f"z_{dim}"), 3), "deviation_score": _num(fp_last.get(f"score_{dim}"), 4), "weight": fp_meta["weights"][dim],
    }


def _dimension_series(dim, feats, fp, window_slice) -> list[dict]:
    display = np.expm1 if dim == "log_volume" else (lambda v: v)
    rows = []
    for i in range(window_slice.start, window_slice.stop):
        med, scale, value = fp[f"median_{dim}"].iloc[i], fp[f"scale_{dim}"].iloc[i], feats[dim].iloc[i]
        rows.append({"date": feats["trading_date"].iloc[i].strftime("%Y-%m-%d"), "value": _num(display(value)), "median": _num(display(med)),
                     "lower": _num(display(med - 2 * scale)), "upper": _num(display(med + 2 * scale)), "robust_z": _num(fp[f"z_{dim}"].iloc[i], 3)})
    return rows


def _news_view(item: dict, symbol: str) -> dict:
    link = next((l for l in item.get("links", []) if l["symbol"] == symbol), None)
    return {"news_id": item["news_id"], "headline": item["headline"], "source": item.get("source"), "url": item.get("url"), "published_at": item["published_at"],
            "is_demo": item.get("is_demo", False), "sentiment": item.get("sentiment"), "entity": link}


def _sentiment_summary(items: list[dict]) -> dict:
    scored = [item["sentiment"] for item in items if item.get("sentiment")]
    counts = {label: sum(1 for s in scored if s["label"] == label) for label in ("positive", "neutral", "negative")}
    return {"count": len(items), "scored": len(scored), "labels": counts, "mean_score": round(float(np.mean([s["sentiment_score"] for s in scored])), 4) if scored else None}
