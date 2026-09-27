"""Market data for the API: provider → validation → cache, with stored-price fallback. Never invents values."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pandas as pd

from ml import config
from ml.data.sessions import is_session_in_progress, to_utc
from ml.data import cache, store
from ml.data.assets import all_assets, get_asset
from ml.data.market_providers import ProviderError, YahooChartProvider, provider_for
from ml.pipelines.intelligence import load_market

logger = logging.getLogger(__name__)
QUOTE_WORKERS = 6


def _market_state(quote: dict, is_demo: bool) -> str:
    """OPEN only when the NSE session clock is running AND the provider's last trade is recent (holidays stay CLOSED)."""
    if is_demo:
        return "DEMO"
    now = datetime.now(timezone.utc)
    if not quote.get("market_time") or not is_session_in_progress(pd.Timestamp(now).tz_convert(config.MARKET_TIMEZONE).date(), now):
        return "CLOSED"
    return "OPEN" if now - to_utc(quote["market_time"]) < timedelta(minutes=30) else "CLOSED"


def _source(provider, stale: bool = False, fetched_at: str | None = None) -> dict:
    return {"provider": provider.name, "is_demo": provider.is_demo, "stale": stale, "fetched_at": fetched_at or store.now_iso()}


def get_quote(symbol: str) -> dict:
    provider = provider_for(symbol)

    def fetch():
        quote = provider.get_quote(symbol)
        asset = get_asset(symbol)
        if asset:
            quote["name"] = asset.name
        return {**quote, "exchange": asset.exchange if asset else "NSE", "market_state": _market_state(quote, provider.is_demo), "data_source": _source(provider)}

    return cache.get_or_set(f"quote:{symbol}", config.QUOTE_CACHE_SECONDS, fetch)


def _quote_or_error(symbol: str) -> dict:
    try:
        return {"symbol": symbol, "status": "ok", "quote": get_quote(symbol)}
    except ProviderError as error:
        return {"symbol": symbol, "status": "unavailable", "error": str(error), "quote": None}


def get_quotes(symbols: list[str]) -> list[dict]:
    """Batch quotes fetched concurrently (small pool, provider-friendly); a failed symbol is returned
    with an explicit error instead of values. Order matches the request."""
    with ThreadPoolExecutor(max_workers=QUOTE_WORKERS) as pool:
        return list(pool.map(_quote_or_error, symbols))


def get_history(symbol: str, limit: int) -> dict:
    def fetch():
        bars, source, report = load_market(symbol)
        return bars, source, report

    bars, source, report = cache.get_or_set(f"history:{symbol}", config.HISTORY_CACHE_SECONDS, fetch)
    tail = bars.tail(limit)
    return {
        "symbol": symbol, "interval": "1d", "data_source": source, "validation": report,
        "bars": [{"timestamp": row.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"), "open": round(row.open, 4), "high": round(row.high, 4), "low": round(row.low, 4),
                  "close": round(row.close, 4), "volume": None if row.volume != row.volume else int(row.volume)} for row in tail.itertuples(index=False)],
    }


def search(query: str) -> list[dict]:
    lowered = query.lower()
    local = [asset.to_dict() for asset in all_assets() if lowered in asset.symbol.lower() or lowered in asset.name.lower()]
    for item in local:
        item["analysed"] = True
    if config.data_mode() == "demo":
        return local
    try:
        remote = YahooChartProvider().search(query)
    except ProviderError:
        logger.info("Remote symbol search unavailable; returning local matches only")
        return local
    known = {item["symbol"] for item in local}
    return (local + [{**item, "analysed": False} for item in remote if item["symbol"] not in known])[:10]
