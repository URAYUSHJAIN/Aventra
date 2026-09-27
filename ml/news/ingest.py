"""News branch of the pipeline: fetch → clean/dedupe → entity linking → FinBERT → store."""
from __future__ import annotations

import json
import logging

from ml import config
from ml.data import cache, store
from ml.data.assets import Asset
from ml.news.entity import link_entities
from ml.news.finbert import FinBertUnavailable, get_news_analysis_service
from ml.news.preprocessing import clean_text, deduplicate
from ml.news.providers import NewsProviderError, news_provider_for

logger = logging.getLogger(__name__)


def _from_store(symbol: str) -> list[dict]:
    items = []
    for row in store.load_news(symbol, limit=200):
        sentiment = None
        if row.get("label"):
            sentiment = {key: row[key] for key in ("label", "positive_probability", "neutral_probability", "negative_probability", "sentiment_score", "confidence", "model", "model_version")}
        items.append({
            "news_id": row["news_id"], "headline": row["headline"], "summary": row["summary"], "source": row["source"], "url": row["url"],
            "published_at": row["published_at"], "provider": row["provider"], "is_demo": bool(row["is_demo"]), "sentiment": sentiment,
            "links": [{"symbol": row["symbol"], "entity_match_confidence": row["entity_match_confidence"], "mapping_method": row["mapping_method"]}],
        })
    return items


def _cached_demo_sentiment() -> dict[str, dict]:
    path = config.DEMO_DIR / "sentiment.json"
    if not path.is_file():
        return {}
    return {item["news_id"]: item for item in json.loads(path.read_text(encoding="utf-8"))["items"]}


def ingest_news(symbol: str, asset: Asset) -> dict:
    provider = news_provider_for(symbol)
    report = {"provider": provider.name, "is_demo": provider.is_demo, "fetched_at": store.now_iso(), "status": "ok", "message": None}
    try:
        raw = cache.get_or_set(f"news:{symbol}", config.NEWS_CACHE_SECONDS, lambda: provider.search(asset.name))
    except NewsProviderError as error:
        logger.warning("News provider failed for %s: %s", symbol, error)
        items = _from_store(symbol)
        report.update(status="stale_cache" if items else "unavailable", message="Live news provider unavailable; showing previously stored news." if items else "News context unavailable.")
        report["items"], report["duplicates_removed"] = items, 0
        report["sentiment_status"] = "stored" if items else "unavailable"
        return report

    cleaned = [{**item, "headline": clean_text(item["headline"]), "summary": clean_text(item.get("summary")) or None} for item in raw]
    items, removed = deduplicate(cleaned)
    linked = []
    for item in items:
        item["links"] = link_entities(item["headline"], item.get("summary") or "", item.get("symbols"))
        if any(link["symbol"] == symbol for link in item["links"]):
            linked.append(item)
    report["duplicates_removed"] = removed
    report["unlinked_dropped"] = len(items) - len(linked)
    store.upsert_news(linked)

    known = store.sentiment_for([item["news_id"] for item in linked])
    missing = [item for item in linked if item["news_id"] not in known]
    report["sentiment_status"] = "ok"
    if missing:
        try:
            results = get_news_analysis_service().analyze_many([item["headline"] for item in missing])
            fresh = {item["news_id"]: result for item, result in zip(missing, results) if result}
        except FinBertUnavailable:
            fresh = {}
            cached = _cached_demo_sentiment() if provider.is_demo else {}
            for item in missing:
                if item["news_id"] in cached:
                    fresh[item["news_id"]] = {**cached[item["news_id"]], "model_version": cached[item["news_id"]].get("model_version")}
            report["sentiment_status"] = "cached_demo_outputs" if fresh else "unavailable"
            report["message"] = "FinBERT is unavailable; " + ("using stored FinBERT outputs for the demo headlines." if fresh else "news sentiment could not be computed.")
        store.upsert_sentiment(fresh)
        known.update(store.sentiment_for(list(fresh)))
    for item in linked:
        row = known.get(item["news_id"])
        item["sentiment"] = {key: row[key] for key in ("label", "positive_probability", "neutral_probability", "negative_probability", "sentiment_score", "confidence", "model", "model_version")} if row else None
    # Previously stored articles (older than the provider's search window) keep their context for older anomalies.
    fresh_ids = {item["news_id"] for item in linked}
    history = [item for item in _from_store(symbol) if item["news_id"] not in fresh_ids and item["is_demo"] == provider.is_demo]
    report["fresh_count"], report["stored_history_count"] = len(linked), len(history)
    report["items"] = sorted(linked + history, key=lambda item: item["published_at"], reverse=True)
    return report
