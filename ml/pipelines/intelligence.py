"""End-to-end intelligence pipeline for one instrument (ML Pipeline §54), asset-aware and provider-agnostic.

Instrument Master → provider router (real data only) → validation → temporal alignment → capability-based features
→ behavioural fingerprint → anomaly detection → news + FinBERT → cross-source correlation → temporal analysis →
risk → evidence chain. The ML stages never see which provider supplied the data; provenance is carried alongside.
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
from ml.data.market_data import capability_profile, load_series
from ml.data.sessions import align_to_session, iso, session_bounds
from ml.evidence.chain import build_evidence, build_explanation
from ml.features.engineering import FEATURE_DEFINITIONS, compute_features
from ml.features.sets import FEATURE_SETS, fingerprint_version, select_set, thresholds_version, version as feature_set_version
from ml.fingerprint.baseline import compute_fingerprint, fingerprint_level
from ml.instruments import ids
from ml.news.ingest import ingest_news
from ml.pipelines import artifacts
from ml.providers import registry
from ml.risk.scoring import compute_risk
from ml.temporal.analysis import lead_lag

logger = logging.getLogger(__name__)
DISCLAIMER = "Aventra provides analytical signals and evidence, not financial advice or guaranteed predictions."
CHANGE_POINT_COLUMNS = {"yield": ("change_bp",), "close": ("log_return",), "close_volume": ("log_return", "log_volume"), "ohlcv": ("log_return", "log_volume")}


class UnknownAsset(LookupError):
    code = "INSTRUMENT_NOT_FOUND"


class InsufficientHistory(ValueError):
    code = "INSUFFICIENT_HISTORY"


def _num(value, digits: int = 6):
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(value) or math.isinf(value) else round(value, digits)


def resolve_instrument(raw_id: str) -> dict:
    """Validated canonical ID → master row (with aliases and provider mappings)."""
    iid = str(ids.parse(raw_id))
    instrument = store.get_instrument(iid)
    if instrument is None:
        raise UnknownAsset(f"{iid} is not in the Instrument Master. Search for the instrument first.")
    return instrument


# --- benchmark ----------------------------------------------------------------------------------
def benchmark_for(instrument: dict) -> str | None:
    """Documented benchmark rules (no benchmark is invented when none applies or none is available)."""
    if instrument.get("benchmark_id"):
        return instrument["benchmark_id"]
    cls, country, exchange = instrument["asset_class"], instrument.get("country"), instrument.get("exchange")
    if country == "IN" and cls in {"equity", "etf", "reit", "invit"}:
        return "IDX:NSE-NIFTY"           # Nifty 50 (Upstox index listing)
    if exchange == "BINANCE" and not instrument["instrument_id"].startswith("CRYPTO:BTC-"):
        return "CRYPTO:BTC-USDT"
    if exchange == "COINGECKO" and instrument["instrument_id"] != "CRYPTO:CG-bitcoin":
        return "CRYPTO:CG-bitcoin"
    return None


def load_benchmark(instrument: dict) -> tuple[pd.DataFrame | None, dict | None]:
    bench_id = benchmark_for(instrument)
    if not bench_id:
        return None, {"status": "not_applicable"}
    bench = store.get_instrument(bench_id)
    if bench is None:
        return None, {"instrument_id": bench_id, "status": "unavailable", "reason": "benchmark not in Instrument Master"}
    try:
        bars, source, _ = load_series(bench)
        return bars, {"instrument_id": bench_id, "name": bench["name"], "status": "ok", "provider": source["provider"]}
    except (registry.DataUnavailable, ValueError) as error:
        return None, {"instrument_id": bench_id, "name": bench["name"], "status": "unavailable", "reason": getattr(error, "code", str(error))}


# --- anomaly detection ------------------------------------------------------------------------------
def fit_or_load_detector(key: str, train: pd.DataFrame, candidates: tuple, window_start_date: str, source_name: str) -> tuple[UnsupervisedDetector | None, dict]:
    columns = [c for c in candidates if c in train.columns and train[c].notna().mean() > 0.9]
    if not columns:
        return None, {"model": "isolation_forest", "status": "insufficient_features"}
    data_hash = artifacts.training_data_hash(train, columns)
    detector, metadata = artifacts.load_detector(key, "isolation_forest", window_start_date, columns, data_hash)
    if detector is not None:
        return detector, {**metadata, "status": "ok", "loaded_from_artifact": True}
    try:
        detector = UnsupervisedDetector("isolation_forest").fit(train, candidates)
    except InsufficientTrainingData as error:
        return None, {"model": "isolation_forest", "status": "insufficient_history", "reason": str(error)}
    trained_through = str(train["trading_date"].iloc[-1].date())
    metadata = artifacts.save_detector(key, detector, trained_through, source_name, data_hash)
    return detector, {**metadata, "status": "ok", "loaded_from_artifact": False}


def _scoring_window(n: int) -> int:
    """Index where scoring starts; detectors are fitted only on rows before it."""
    return max(n - config.SCORING_WINDOW, min(config.MIN_TRAIN_BARS + config.ROLLING_WINDOW, n))


# --- per-bar assessment -------------------------------------------------------------------------------
def assess_bar(i: int, instrument: dict, feats, fp, stat, ens, dims, news_items, news_status, market_source, change_points) -> dict:
    iid, calendar = instrument["instrument_id"], instrument.get("calendar_code")
    key = ids.safe_key(iid)
    row_fp = fp.iloc[i].to_dict()
    trading_date = feats["trading_date"].iloc[i]
    date_str, stamp = trading_date.strftime("%Y-%m-%d"), trading_date.strftime("%Y%m%d")
    contributing = contributing_features(row_fp, dims, feats.iloc[i])
    anomaly = {
        "anomaly_id": f"AN-{key}-{stamp}", "trading_date": date_str,
        "timestamp": iso(session_bounds(trading_date, calendar)[0]), "anomaly_score": _num(ens["anomaly_score"].iloc[i], 4) or 0.0,
        "severity": ens["severity"].iloc[i] or "LOW", "is_anomaly": bool(ens["is_anomaly"].iloc[i]),
        "scores": {"statistical": _num(stat["statistical_score"].iloc[i], 4), "fingerprint": _num(fp["fingerprint_score"].iloc[i], 4), "isolation_forest": _num(ens["_if"].iloc[i], 4)},
        "model_agreement": _num(ens["model_agreement"].iloc[i], 4) or 0.0, "contributing_features": contributing,
        "score_semantics": "heuristic ensemble score in [0, 1]; not a calibrated probability",
    }
    if news_status in {"unavailable"}:
        open_utc, close_utc = session_bounds(trading_date, calendar)
        correlation = {"status": "news_unavailable", "window": {"session_open": iso(open_utc), "session_close": iso(close_utc), "start": None, "end": None}, "best_score": 0.0, "matches": []}
    else:
        correlation = correlate(trading_date, anomaly["anomaly_score"], contributing, news_items, iid, instrument["name"], calendar)
    risk = compute_risk(anomaly["anomaly_score"], anomaly["scores"]["fingerprint"], anomaly["model_agreement"], correlation, "ok" if news_status != "unavailable" else "unavailable")
    assessment = {"event_id": f"EV-{key}-{stamp}", "trading_date": date_str, "anomaly": anomaly, "correlation": correlation,
                  "risk": risk, "fingerprint_score": anomaly["scores"]["fingerprint"], "window": {"start": correlation["window"]["start"], "end": correlation["window"]["end"]}}
    assessment["evidence"] = build_evidence(assessment, market_source, change_points)
    assessment["explanation"] = build_explanation(assessment, instrument["name"])
    anomaly["explanation"] = assessment["explanation"]["signals"]
    return assessment


def run_intelligence(instrument_id: str, persist: bool = True, force_refresh: bool = False) -> dict:
    started = time.perf_counter()
    instrument = resolve_instrument(instrument_id)
    iid = instrument["instrument_id"]
    profile = capability_profile(instrument)
    set_name = select_set(profile)
    feature_set = FEATURE_SETS[set_name]
    timings: dict[str, float] = {}

    def tick(stage: str, since: float) -> float:
        now = time.perf_counter()
        timings[stage] = round((now - since) * 1000, 1)
        logger.info("pipeline stage=%s instrument=%s status=ok duration_ms=%.1f", stage, iid, timings[stage])
        return now

    t = time.perf_counter()
    bars, market_source, validation = load_series(instrument, force_refresh=force_refresh)
    bench, bench_info = load_benchmark(instrument)
    t = tick("market_data", t)
    feats = compute_features(bars, bench, profile)
    t = tick("features", t)
    needed = max(profile.get("minimum_history", 0), config.FINGERPRINT_MIN_HISTORY + config.ROLLING_WINDOW)
    if len(feats) < needed:
        raise InsufficientHistory(f"{iid} has {len(feats)} usable observations; at least {needed} are required for a reliable behavioural fingerprint.")
    fp, fp_meta = compute_fingerprint(feats, feature_set["fingerprint"])
    t = tick("fingerprint", t)

    n = len(feats)
    start = _scoring_window(n)
    stat = statistical_scores(feats, feature_set["statistical"])
    window_start_date = str(feats["trading_date"].iloc[start].date())
    detector, detector_meta = fit_or_load_detector(ids.safe_key(iid), feats.iloc[:start], feature_set["detector"], window_start_date, market_source["provider"])
    if_scores = detector.score(feats) if detector is not None else np.full(n, np.nan)
    if_scores[:start] = np.nan   # in-sample scores are never reported
    components = pd.DataFrame({"statistical": stat["statistical_score"], "fingerprint": fp["fingerprint_score"], "isolation_forest": if_scores})
    ens = combine(components)
    ens["_if"] = if_scores
    change = detect_change_points(feats.iloc[start:], CHANGE_POINT_COLUMNS[set_name])
    t = tick("anomaly_detection", t)

    news = ingest_news(iid, instrument)
    if news["status"] == "ok" and not news["items"]:
        news["status"] = "no_relevant_news"
    t = tick("news_and_sentiment", t)

    dims = fp_meta["dimensions"]
    flagged = [i for i in range(start, n) if bool(ens["is_anomaly"].iloc[i])]
    args = (instrument, feats, fp, stat, ens, dims, news["items"], news["status"], market_source, change.get("change_points", []))
    events = [assess_bar(i, *args) for i in reversed(flagged)]
    current = assess_bar(n - 1, *args)
    t = tick("correlation_risk_evidence", t)

    trading_dates = list(feats["trading_date"])
    daily_sentiment: dict = {}
    for item in news["items"]:
        if item.get("sentiment"):
            aligned = align_to_session(item["published_at"], trading_dates, instrument.get("calendar_code"))
            if aligned is not None:
                daily_sentiment.setdefault(aligned, []).append(item["sentiment"]["sentiment_score"])
    lead_lag_result = lead_lag(feats.set_index("trading_date")["return_1" if set_name != "yield" else "change_bp"],
                               pd.Series({d: float(np.mean(v)) for d, v in daily_sentiment.items()}, dtype=float))

    last = feats.iloc[-1]
    fp_last = fp.iloc[-1]
    window_slice = slice(start, n)
    versions = {"pipeline": config.PIPELINE_VERSION, "feature_set": feature_set_version(set_name), "fingerprint": fingerprint_version(),
                "thresholds": thresholds_version(), "model": detector_meta.get("model_version")}
    result = {
        "run_id": f"RUN-{ids.safe_key(iid)}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}",
        "instrument_id": iid, "symbol": instrument["symbol"],
        "asset": {"instrument_id": iid, "symbol": instrument["symbol"], "name": instrument["name"], "asset_class": instrument["asset_class"],
                  "exchange": instrument.get("exchange"), "country": instrument.get("country"), "currency": market_source.get("currency") or instrument.get("currency"),
                  "timezone": instrument.get("timezone"), "calendar": instrument.get("calendar_code"), "sector": "", "is_demo": market_source["provider"] == "aventra_demo_dataset"},
        "capabilities": {k: profile.get(k) for k in ("has_ohlc", "has_volume", "value_kind", "minimum_history", "calendar", "timezone", "currency")},
        "feature_set": set_name, "versions": versions,
        "generated_at": store.now_iso(), "pipeline_version": config.PIPELINE_VERSION,
        "data_source": {"market": {**market_source, "is_demo": market_source["provider"] == "aventra_demo_dataset"}, "benchmark": bench_info,
                        "news": {k: v for k, v in news.items() if k != "items"}},
        "validation": validation,
        "market": {
            "latest": {"trading_date": last["trading_date"].strftime("%Y-%m-%d"), "open": _num(last["open"], 6), "high": _num(last["high"], 6), "low": _num(last["low"], 6),
                       "close": _num(last["close"], 6), "volume": _num(last["volume"], 0), "return_1": _num(last["return_1"]), "volatility_20": _num(last["volatility_20"]),
                       "volume_ratio": _num(last["volume_ratio"], 4), "change_bp": _num(last["change_bp"], 3)},
            "series": [
                {"date": feats["trading_date"].iloc[i].strftime("%Y-%m-%d"), "open": _num(feats["open"].iloc[i], 6), "high": _num(feats["high"].iloc[i], 6), "low": _num(feats["low"].iloc[i], 6),
                 "close": _num(feats["close"].iloc[i], 6), "volume": _num(feats["volume"].iloc[i], 0), "anomaly_score": _num(ens["anomaly_score"].iloc[i], 4),
                 "is_anomaly": bool(ens["is_anomaly"].iloc[i]), "severity": ens["severity"].iloc[i]}
                for i in range(start, n)
            ],
        },
        "fingerprint": {
            "as_of": last["trading_date"].strftime("%Y-%m-%d"), "score": _num(fp_last["fingerprint_score"], 4), "level": fingerprint_level(fp_last["fingerprint_score"]),
            "status": fp_last["fingerprint_status"], "version": versions["fingerprint"],
            "dimensions": [_dimension(dim, last, fp_last, fp_meta) for dim in dims],
            "series": {dim: _dimension_series(dim, feats, fp, window_slice) for dim in dims},
            "method": {"baseline": "rolling median / MAD of prior observations (robust z-score)", "window": config.FINGERPRINT_WINDOW, "min_history": config.FINGERPRINT_MIN_HISTORY,
                       "guarded_update_z": config.FINGERPRINT_GUARD_Z, "score_mapping": f"linear from |z|={config.Z_SCORE_FLOOR} (0) to |z|={config.Z_SCORE_CAP} (1)",
                       "weights": fp_meta["weights"], "weights_status": "heuristic (equal weights), not validated"},
        },
        "anomaly": {
            "current": current["anomaly"], "threshold": config.ANOMALY_THRESHOLD, "flagged_count": len(flagged),
            "window": {"start": window_start_date, "end": last["trading_date"].strftime("%Y-%m-%d"), "bars": n - start},
            "ensemble_weights": config.ENSEMBLE_WEIGHTS, "weights_status": "heuristic, configurable (ml/config.py)",
            "severity_bands": [{"min": floor, "label": label} for floor, label in config.SEVERITY_BANDS], "change_points": change,
        },
        "news": {"status": news["status"], "message": news.get("message"), "items": [_news_view(item, iid) for item in news["items"][:40]],
                 "sentiment_summary": _sentiment_summary(news["items"])},
        "current_assessment": current,
        "events": events,
        "lead_lag": lead_lag_result,
        "models": {"isolation_forest": detector_meta, "finbert": {"model": "ProsusAI/finBERT", "status": news.get("sentiment_status")},
                   "semantic": next((e["correlation"].get("semantic_model") for e in [current, *events] if e["correlation"].get("semantic_model")), None)},
        "parameters": {"scoring_window": config.SCORING_WINDOW, "anomaly_threshold": config.ANOMALY_THRESHOLD, "correlation_weights": config.CORRELATION_WEIGHTS,
                       "risk_weights": config.RISK_WEIGHTS, "correlation_lookback_hours": config.CORRELATION_LOOKBACK_HOURS, "correlation_lookahead_hours": config.CORRELATION_LOOKAHEAD_HOURS,
                       "random_seed": config.RANDOM_SEED, "calibration_status": "uncalibrated heuristic defaults"},
        "feature_definitions": {k: v for k, v in FEATURE_DEFINITIONS.items() if k in set(dims) | set(feature_set["detector"])},
        "timings_ms": {**timings, "total": round((time.perf_counter() - started) * 1000, 1)},
        "disclaimer": DISCLAIMER,
    }
    if persist:
        store.save_run(result)
    return result


def _dimension(dim, last, fp_last, fp_meta) -> dict:
    to_display = (lambda v: math.expm1(v) if v is not None else None) if dim == "log_volume" else (lambda v: v)
    unit = "shares" if dim == "log_volume" else ("bp" if dim.endswith("_bp") or dim.startswith("change_") else "fraction")
    median = _num(fp_last.get(f"median_{dim}"))
    q = fp_meta["quantiles"].get(dim, {})
    return {
        "feature": dim, "label": LABELS.get(dim, dim), "unit": unit,
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


def _news_view(item: dict, instrument_id: str) -> dict:
    link = next((l for l in item.get("links", []) if l["instrument_id"] == instrument_id), None)
    return {"news_id": item["news_id"], "headline": item["headline"], "source": item.get("source"), "url": item.get("url"), "published_at": item["published_at"],
            "is_demo": item.get("is_demo", False), "sentiment": item.get("sentiment"), "entity": link}


def _sentiment_summary(items: list[dict]) -> dict:
    scored = [item["sentiment"] for item in items if item.get("sentiment")]
    counts = {label: sum(1 for s in scored if s["label"] == label) for label in ("positive", "neutral", "negative")}
    return {"count": len(items), "scored": len(scored), "labels": counts, "mean_score": round(float(np.mean([s["sentiment_score"] for s in scored])), 4) if scored else None}
