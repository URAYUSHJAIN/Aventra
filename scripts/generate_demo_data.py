"""Generate the deterministic SYNTHETIC demo dataset in data/demo/ (ML Pipeline §56–57).

The asset "Aventra Synthetic Demo Asset" (symbol DEMO) and all its headlines are
fictional. The scenario injects, on a known session, a volume spike + price drop
with negative news published during the session, so the full pipeline
(fingerprint → anomaly → news → correlation → risk → evidence) can be demonstrated
without external APIs. sentiment.json is produced by running the real local FinBERT
model on the synthetic headlines — it is cached model output, not hand-written values.

Run from the repo root:  py -3.12 -m scripts.generate_demo_data
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, time, timezone

import numpy as np
import pandas as pd

from ml import config
from ml.news.preprocessing import news_id_for

SEED = 20260927
N_SESSIONS = 620
END_DATE = "2026-06-30"
EVENT_OFFSET = 12          # the scenario session is the 12th-last session
SOURCE = "Aventra Demo Newswire (synthetic)"


def _session_open_utc(day: pd.Timestamp) -> pd.Timestamp:
    local = pd.Timestamp(datetime.combine(day.date(), time(*config.SESSION_OPEN))).tz_localize(config.MARKET_TIMEZONE)
    return local.tz_convert("UTC")


def _at(day: pd.Timestamp, hh: int, mm: int) -> str:
    local = pd.Timestamp(datetime.combine(day.date(), time(hh, mm))).tz_localize(config.MARKET_TIMEZONE)
    return local.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def build_market(rng: np.random.Generator) -> tuple[pd.DataFrame, pd.Timestamp]:
    days = pd.bdate_range(end=END_DATE, periods=N_SESSIONS)
    returns = rng.normal(0.0003, 0.012, N_SESSIONS)
    volume = np.exp(rng.normal(np.log(1_200_000), 0.22, N_SESSIONS))
    gaps = rng.normal(0, 0.003, N_SESSIONS)
    ranges = np.abs(rng.normal(0.014, 0.004, N_SESSIONS))
    event = N_SESSIONS - EVENT_OFFSET
    # Scenario: T1 volume spike + T2 price deviation on the event session, elevated activity afterwards.
    returns[event], volume[event], gaps[event], ranges[event] = -0.068, volume[event] * 4.6, -0.012, 0.085
    returns[event + 1], volume[event + 1], ranges[event + 1] = -0.021, volume[event + 1] * 2.4, 0.045
    for k in range(event + 2, event + 6):
        returns[k] *= 1.8
        ranges[k] *= 1.6
    close = 1450 * np.cumprod(1 + returns)
    prev_close = np.concatenate([[1450.0], close[:-1]])
    open_ = prev_close * (1 + gaps)
    high = np.maximum(open_, close) * (1 + ranges * 0.45)
    low = np.minimum(open_, close) * (1 - ranges * 0.45)
    frame = pd.DataFrame({
        "symbol": "DEMO", "timestamp": [_session_open_utc(d).strftime("%Y-%m-%dT%H:%M:%SZ") for d in days],
        "open": open_.round(2), "high": high.round(2), "low": low.round(2), "close": close.round(2), "adj_close": close.round(2), "volume": volume.round(0).astype(int),
    })
    return frame, days[event]


def build_news(days: pd.DatetimeIndex, event_day: pd.Timestamp) -> list[dict]:
    routine = [
        (-400, 11, 20, "Aventra Demo Asset reports quarterly revenue in line with estimates"),
        (-340, 16, 45, "Aventra Demo Asset announces interim dividend for shareholders"),
        (-280, 9, 50, "Aventra Demo Asset opens new logistics facility in Pune"),
        (-210, 17, 30, "Aventra Demo Asset quarterly profit rises on steady demand"),
        (-150, 12, 5, "Aventra Demo Asset appoints new chief financial officer"),
        (-95, 18, 10, "Aventra Demo Asset signs supply agreement with regional distributor"),
        (-60, 10, 40, "Aventra Demo Asset maintains full-year guidance"),
        (-30, 15, 55, "Aventra Demo Asset completes planned plant maintenance on schedule"),
    ]
    scenario = [
        (0, 10, 5, "Aventra Demo Asset shares fall sharply after regulator opens investigation into accounting practices"),
        (0, 13, 40, "Aventra Demo Asset says it will cooperate fully with regulator's probe"),
        (1, 8, 30, "Brokerages cut Aventra Demo Asset price targets, citing uncertainty from the accounting investigation"),
    ]
    index = {d.normalize(): i for i, d in enumerate(days)}
    event_index = index[event_day.normalize()]
    items = []
    for offset, hh, mm, headline in routine + scenario:
        day = days[event_index + offset]
        items.append({"news_id": news_id_for(headline, SOURCE), "headline": headline, "summary": None, "source": SOURCE, "url": None,
                      "published_at": _at(day, hh, mm), "symbols": ["DEMO"], "is_demo": True})
    return items


def build_sentiment(items: list[dict]) -> dict | None:
    from ml.news.finbert import FinBertUnavailable, get_news_analysis_service
    try:
        service = get_news_analysis_service()
        results = service.analyze_many([item["headline"] for item in items])
    except FinBertUnavailable:
        logging.warning("FinBERT unavailable: sentiment.json not written (the demo will run FinBERT live when available).")
        return None
    return {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "note": "Cached outputs of the local FinBERT model on the synthetic demo headlines.",
            "items": [{"news_id": item["news_id"], **result} for item, result in zip(items, results)]}


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    rng = np.random.default_rng(SEED)
    market, event_day = build_market(rng)
    days = pd.bdate_range(end=END_DATE, periods=N_SESSIONS)
    news = build_news(days, event_day)
    config.DEMO_DIR.mkdir(parents=True, exist_ok=True)
    market.to_csv(config.DEMO_DIR / "market.csv", index=False)
    (config.DEMO_DIR / "news.json").write_text(json.dumps({"is_synthetic": True, "items": news}, indent=2), encoding="utf-8")
    sentiment = build_sentiment(news)
    if sentiment:
        (config.DEMO_DIR / "sentiment.json").write_text(json.dumps(sentiment, indent=2), encoding="utf-8")
    manifest = {
        "is_synthetic": True, "asset": "DEMO (Aventra Synthetic Demo Asset — fictional)", "seed": SEED, "sessions": N_SESSIONS,
        "date_range": [str(days[0].date()), str(days[-1].date())], "scenario_session": str(event_day.date()),
        "scenario": ["normal behaviour before the scenario session", "volume ≈4.6× typical and a −6.8% close-to-close move on the scenario session",
                     "negative synthetic headline published 10:05 IST during that session", "follow-up headlines at 13:40 IST and the next morning",
                     "elevated volume/volatility for the following sessions"],
        "generator": "scripts/generate_demo_data.py",
        "warning": "Synthetic data for demonstration and pipeline testing only. It is not market data and must not be used for performance claims.",
    }
    (config.DEMO_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logging.info("Demo dataset written to %s (scenario session %s)", config.DEMO_DIR, event_day.date())


if __name__ == "__main__":
    main()
