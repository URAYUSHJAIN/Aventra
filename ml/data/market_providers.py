"""Market-data provider abstraction (ML Pipeline §6.1).

Providers return raw OHLCV frames with UTC timestamps; validation happens in
`ml.data.validation`. No provider ever invents values: failures raise
`ProviderError` and the caller decides how to degrade (cached data or an
explicit "unavailable" state).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

from ml import config
from ml.data.assets import provider_symbol_for

logger = logging.getLogger(__name__)
_HEADERS = {"User-Agent": "Mozilla/5.0 (Aventra research prototype)", "Accept": "application/json"}


class ProviderError(RuntimeError):
    """kind: 'not_found' (unknown symbol), 'unavailable' (network/HTTP/rate limit), 'invalid_response'."""

    def __init__(self, message: str, kind: str = "unavailable"):
        super().__init__(message)
        self.kind = kind


class MarketDataProvider:
    name = "base"
    is_demo = False

    def get_history(self, symbol: str, range_: str = config.HISTORY_RANGE) -> pd.DataFrame:
        raise NotImplementedError

    def get_quote(self, symbol: str) -> dict:
        raise NotImplementedError


class YahooChartProvider(MarketDataProvider):
    """Yahoo Finance chart endpoint (unofficial; may change or rate-limit without notice)."""

    name = "yahoo_finance_chart"
    base_url = "https://query1.finance.yahoo.com"

    def _chart(self, symbol: str, range_: str, interval: str) -> dict:
        provider_symbol = provider_symbol_for(symbol)
        url = f"{self.base_url}/v8/finance/chart/{requests.utils.quote(provider_symbol, safe='')}"
        try:
            response = requests.get(url, params={"range": range_, "interval": interval}, headers=_HEADERS, timeout=config.PROVIDER_TIMEOUT_SECONDS)
        except requests.RequestException as error:
            raise ProviderError(f"Market provider request failed for {symbol}.") from error
        if response.status_code == 404:
            raise ProviderError(f"No market data found for {symbol}.", kind="not_found")
        if response.status_code == 429:
            raise ProviderError("Market provider rate limit reached.")
        if not response.ok:
            raise ProviderError(f"Market provider returned HTTP {response.status_code}.")
        try:
            result = response.json()["chart"]["result"][0]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise ProviderError("Market provider returned an unexpected response.", kind="invalid_response") from error
        if not result or not result.get("timestamp"):
            raise ProviderError(f"No market observations returned for {symbol}.", kind="not_found")
        return result

    @staticmethod
    def _frame(result: dict) -> pd.DataFrame:
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        frame = pd.DataFrame({
            "timestamp": pd.to_datetime(result["timestamp"], unit="s", utc=True),
            "open": quote.get("open"), "high": quote.get("high"), "low": quote.get("low"),
            "close": quote.get("close"), "volume": quote.get("volume"),
        })
        adj = (result.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose")
        frame["adj_close"] = adj if adj is not None and len(adj) == len(frame) else np.nan
        return frame

    def get_history(self, symbol: str, range_: str = config.HISTORY_RANGE) -> pd.DataFrame:
        frame = self._frame(self._chart(symbol, range_, "1d"))
        frame["symbol"] = symbol
        frame["source"] = self.name
        return frame

    def get_quote(self, symbol: str) -> dict:
        result = self._chart(symbol, "1d", "5m")
        meta = result.get("meta", {})
        price = meta.get("regularMarketPrice")
        if price is None:
            raise ProviderError(f"Quote for {symbol} is incomplete.", kind="invalid_response")
        previous = meta.get("previousClose") or meta.get("chartPreviousClose")
        intraday = self._frame(result).dropna(subset=["close"])
        market_time = meta.get("regularMarketTime")
        return {
            "symbol": symbol,
            "name": meta.get("longName") or meta.get("shortName") or symbol,
            "currency": meta.get("currency"),
            "price": float(price),
            "previous_close": float(previous) if previous else None,
            "change_pct": round((price - previous) / previous * 100, 4) if previous else None,
            "volume": int(meta["regularMarketVolume"]) if meta.get("regularMarketVolume") is not None else None,
            "day_high": meta.get("regularMarketDayHigh"),
            "day_low": meta.get("regularMarketDayLow"),
            "market_time": datetime.fromtimestamp(market_time, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if market_time else None,
            "intraday": [{"timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "close": round(float(close), 4)} for ts, close in zip(intraday["timestamp"], intraday["close"])],
            "interval": "5m",
        }

    def search(self, query: str) -> list[dict]:
        try:
            response = requests.get(f"{self.base_url}/v1/finance/search", params={"q": query, "quotesCount": 10, "newsCount": 0}, headers=_HEADERS, timeout=config.PROVIDER_TIMEOUT_SECONDS)
            response.raise_for_status()
            quotes = response.json().get("quotes", [])
        except (requests.RequestException, ValueError) as error:
            raise ProviderError("Symbol search is unavailable.") from error
        return [
            {"symbol": item["symbol"][:-3], "name": item.get("longname") or item.get("shortname") or item["symbol"][:-3], "exchange": "NSE"}
            for item in quotes if item.get("quoteType") == "EQUITY" and str(item.get("symbol", "")).endswith(".NS")
        ]


class DemoMarketProvider(MarketDataProvider):
    """Deterministic SYNTHETIC data from data/demo/market.csv (generated by scripts/generate_demo_data.py)."""

    name = "aventra_demo_dataset"
    is_demo = True

    def _load(self) -> pd.DataFrame:
        path = config.DEMO_DIR / "market.csv"
        if not path.is_file():
            raise ProviderError("Demo dataset is missing. Run: py -3.12 -m scripts.generate_demo_data", kind="unavailable")
        return pd.read_csv(path, parse_dates=["timestamp"])

    def get_history(self, symbol: str, range_: str = config.HISTORY_RANGE) -> pd.DataFrame:
        frame = self._load()
        frame = frame[frame["symbol"] == symbol]
        if frame.empty:
            raise ProviderError(f"{symbol} is not part of the demo dataset.", kind="not_found")
        frame = frame.copy()
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame["source"] = self.name
        return frame.reset_index(drop=True)

    def get_quote(self, symbol: str) -> dict:
        frame = self.get_history(symbol).dropna(subset=["close"])
        last, previous = frame.iloc[-1], frame.iloc[-2]
        recent = frame.tail(30)
        return {
            "symbol": symbol, "name": "Aventra Synthetic Demo Asset", "currency": "INR",
            "price": float(last["close"]), "previous_close": float(previous["close"]),
            "change_pct": round((last["close"] - previous["close"]) / previous["close"] * 100, 4),
            "volume": int(last["volume"]), "day_high": float(last["high"]), "day_low": float(last["low"]),
            "market_time": last["timestamp"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "intraday": [{"timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "close": round(float(close), 4)} for ts, close in zip(recent["timestamp"], recent["close"])],
            "interval": "1d",
        }


def provider_for(symbol: str) -> MarketDataProvider:
    """DEMO (and every symbol in demo mode) uses the local synthetic dataset; everything else uses Yahoo."""
    if symbol == "DEMO" or config.data_mode() == "demo":
        return DemoMarketProvider()
    return YahooChartProvider()
