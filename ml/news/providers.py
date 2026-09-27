"""News providers.

Production news source: Alpha Vantage NEWS_SENTIMENT (approved provider; ALPHAVANTAGE_API_KEY; shares the Alpha
Vantage daily request budget). It is queried by ticker tags — US equities/ETFs (`AAPL`), crypto (`CRYPTO:BTC`) and
currencies (`FOREX:USD`); its per-ticker relevance scores become explicit entity links. Alpha Vantage's own
sentiment is not used: Aventra runs FinBERT on every headline.

Google News RSS was removed (Phase 7): news.google.com/robots.txt disallows /rss/search for all user agents, and
it was never part of the Phase 0 verified provider set (AGENTS.md C23). Assets without a permitted news source get
an explicit "news unavailable" state — never substituted content.
"""
from __future__ import annotations

import json
import os

import pandas as pd

from ml import config
from ml.news.preprocessing import clean_text, news_id_for
from ml.providers import http
from ml.providers.base import ProviderError

US_VENUES = {"XNAS", "XNYS", "ARCX", "XASE", "BATS"}
# AV relevance_score (0–1) at/above which a provider ticker tag is accepted as an explicit entity link.
TAG_MIN_RELEVANCE = 0.6


class NewsProviderError(RuntimeError):
    def __init__(self, message: str, code: str = "PROVIDER_UNAVAILABLE"):
        super().__init__(message)
        self.code = code


class NewsProvider:
    name = "base"
    is_demo = False

    def search(self, instrument: dict) -> list[dict]:
        raise NotImplementedError


def av_tickers(instrument: dict) -> list[str] | None:
    """Alpha Vantage news tags for an instrument, or None when AV news does not cover it."""
    cls, exchange, symbol = instrument["asset_class"], instrument.get("exchange"), instrument.get("symbol") or ""
    iid = instrument["instrument_id"]
    if cls in {"equity", "etf", "reit"} and exchange in US_VENUES:
        return [symbol]
    if cls == "crypto":
        base = iid.split(":", 1)[1].split("-")[0] if exchange == "BINANCE" else symbol
        return [f"CRYPTO:{base.upper()}"] if base else None
    if cls == "forex" and len(symbol) == 6:
        return [f"FOREX:{symbol[:3]}", f"FOREX:{symbol[3:]}"]
    return None


class AlphaVantageNewsProvider(NewsProvider):
    name = "alpha_vantage_news"

    def search(self, instrument: dict) -> list[dict]:
        tickers = av_tickers(instrument)
        key = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
        if not key:
            raise NewsProviderError("Alpha Vantage news is not configured (ALPHAVANTAGE_API_KEY is not set).")
        response = http.request("alpha_vantage", "NEWS_SENTIMENT", "https://www.alphavantage.co/query", per_minute=5,
                                daily_budget=int(os.getenv("AVENTRA_ALPHAVANTAGE_DAILY_BUDGET", "25")),
                                params={"function": "NEWS_SENTIMENT", "tickers": ",".join(tickers), "limit": 200, "sort": "LATEST", "apikey": key})
        payload = http.json_or_raise(response, "alpha_vantage")
        if "feed" not in payload:
            message = payload.get("Information") or payload.get("Note") or payload.get("Error Message") or "unexpected response"
            raise NewsProviderError(f"Alpha Vantage news: {str(message)[:160]}", "RATE_LIMITED" if "rate" in str(message).lower() else "PROVIDER_UNAVAILABLE")
        items = []
        wanted = set(tickers)
        for entry in payload["feed"]:
            try:
                # time_published is YYYYMMDDTHHMMSS; Alpha Vantage does not document its timezone — treated as UTC (documented assumption).
                published = pd.Timestamp(pd.to_datetime(entry["time_published"], format="%Y%m%dT%H%M%S"), tz="UTC")
            except (KeyError, ValueError):
                continue
            title = clean_text(entry.get("title"))
            if not title:
                continue
            tags = {t.get("ticker"): float(t.get("relevance_score") or 0) for t in entry.get("ticker_sentiment", [])}
            covered = [tags.get(t, 0.0) for t in wanted]
            # Explicit link only when every requested tag is present and the weakest relevance clears the threshold.
            explicit = [instrument["instrument_id"]] if covered and min(covered) >= TAG_MIN_RELEVANCE else []
            items.append({"news_id": news_id_for(title, entry.get("source")), "headline": title, "summary": clean_text(entry.get("summary")) or None,
                          "source": entry.get("source"), "url": entry.get("url"), "published_at": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
                          "instrument_ids": explicit, "provider": self.name, "is_demo": False,
                          "provider_meta": {"tag_relevance": {t: tags.get(t) for t in wanted}, "timezone_assumed": "UTC"}})
        return items


class DemoNewsProvider(NewsProvider):
    """SYNTHETIC headlines from data/demo/news.json — automated tests only (TEST:DEMO), never user-facing."""

    name = "aventra_demo_dataset"
    is_demo = True

    def search(self, instrument: dict) -> list[dict]:
        path = config.DEMO_DIR / "news.json"
        if not path.is_file():
            raise NewsProviderError("Test news fixture is missing. Run: py -3.12 -m scripts.generate_demo_data")
        records = json.loads(path.read_text(encoding="utf-8"))["items"]
        return [{**item, "instrument_ids": ["TEST:DEMO"], "provider": self.name, "is_demo": True} for item in records]


def news_provider_for(instrument: dict) -> tuple[NewsProvider | None, str | None]:
    """(provider, None) or (None, reason) when no permitted news source covers the instrument."""
    if instrument.get("instrument_id", "").startswith("TEST:"):
        return (DemoNewsProvider(), None) if config.synthetic_test_data_enabled() else (None, "synthetic test data disabled")
    if av_tickers(instrument) is None:
        return None, f"No permitted news source covers {instrument['asset_class']} instruments on {instrument.get('exchange')}."
    return AlphaVantageNewsProvider(), None


__all__ = ["NewsProvider", "NewsProviderError", "AlphaVantageNewsProvider", "DemoNewsProvider", "news_provider_for", "av_tickers", "ProviderError"]
