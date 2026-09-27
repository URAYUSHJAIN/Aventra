"""Alpha Vantage — US equities/ETFs and BSE equities (daily OHLCV), symbol search, US listing status.

Verified (Phase 0): BSE daily history since 2005 via the documented example; free key 25 requests/day;
"unlimited" for verified educational projects (on application). Requires ALPHAVANTAGE_API_KEY.
Daily bars from TIME_SERIES_DAILY are NOT split/dividend adjusted (`adjusted=False` is recorded).
"""
from __future__ import annotations

import csv
import io
import os

import pandas as pd

from ml.data.calendars import session_open_utc
from ml.instruments import ids
from ml.instruments.master import alias_rows, instrument_row, name_aliases
from ml.providers import http
from ml.providers.base import InstrumentNotSupported, MalformedResponse, Provider, ProviderCapability, RateLimited, Series

BASE = "https://www.alphavantage.co/query"
US_EXCHANGES = {"NASDAQ": "XNAS", "NYSE": "XNYS", "NYSE ARCA": "ARCX", "NYSE MKT": "XASE", "BATS": "BATS"}


class AlphaVantageProvider(Provider):
    name = "alpha_vantage"
    capability = ProviderCapability(
        asset_classes=("equity", "etf", "reit"), exchanges=("XNAS", "XNYS", "ARCX", "XASE", "BATS", "XBOM"),
        fields=("open", "high", "low", "close", "volume"), listing=True, search=True, credential_env="ALPHAVANTAGE_API_KEY",
        rate_limit_per_minute=5, daily_budget=int(os.getenv("AVENTRA_ALPHAVANTAGE_DAILY_BUDGET", "25")),
        terms="Free key: 25 requests/day; educational projects may apply for unlimited access. Full ToS not reviewed (docs/06).",
    )

    def _get(self, endpoint: str, params: dict):
        self.require_available()
        response = http.request(self.name, endpoint, BASE, per_minute=self.capability.rate_limit_per_minute, daily_budget=self.capability.daily_budget,
                                params={**params, "apikey": self.credential()})
        return response

    @staticmethod
    def _check(payload: dict, provider: str):
        if not isinstance(payload, dict):
            raise MalformedResponse("Alpha Vantage returned an unexpected payload.", provider)
        if "Error Message" in payload:
            raise InstrumentNotSupported(payload["Error Message"][:200], provider)
        message = payload.get("Note") or payload.get("Information")
        if message:
            if "premium" in message.lower():
                raise InstrumentNotSupported("Alpha Vantage: this request needs a premium plan.", provider)
            raise RateLimited(f"Alpha Vantage: {message[:160]}", provider)

    def derive_symbol(self, instrument: dict) -> str | None:
        if instrument.get("exchange") == "XBOM":
            return f"{instrument['symbol']}.BSE"
        if instrument.get("exchange") in {"XNAS", "XNYS", "ARCX", "XASE", "BATS"}:
            return instrument["symbol"]
        return None

    def history(self, instrument: dict, provider_symbol: str, start=None) -> Series:
        payload = http.json_or_raise(self._get("TIME_SERIES_DAILY", {"function": "TIME_SERIES_DAILY", "symbol": provider_symbol, "outputsize": "full"}), self.name)
        try:
            self._check(payload, self.name)
        except InstrumentNotSupported as error:
            if "premium" not in str(error):
                raise
            payload = http.json_or_raise(self._get("TIME_SERIES_DAILY", {"function": "TIME_SERIES_DAILY", "symbol": provider_symbol, "outputsize": "compact"}), self.name)
            self._check(payload, self.name)
        series = payload.get("Time Series (Daily)")
        if not isinstance(series, dict) or not series:
            raise MalformedResponse("Alpha Vantage response has no daily series.", self.name)
        calendar = instrument.get("calendar_code")
        rows = [{"timestamp": session_open_utc(day, calendar), "open": float(v["1. open"]), "high": float(v["2. high"]), "low": float(v["3. low"]),
                 "close": float(v["4. close"]), "volume": float(v["5. volume"])} for day, v in series.items()]
        frame = pd.DataFrame(rows)
        if start is not None:
            frame = frame[frame["timestamp"] >= pd.Timestamp(start, tz="UTC")]
        return Series(frame, self.name, provider_symbol, instrument.get("currency"), instrument.get("timezone"), adjusted=False,
                      meta={"endpoint": "TIME_SERIES_DAILY", "output": "full" if len(rows) > 100 else "compact"})

    def list_instruments(self):
        response = self._get("LISTING_STATUS", {"function": "LISTING_STATUS"})
        reader = csv.DictReader(io.StringIO(response.text))
        rows, aliases, mappings = [], [], []
        for record in reader:
            exchange = US_EXCHANGES.get((record.get("exchange") or "").upper())
            symbol = (record.get("symbol") or "").strip().upper()
            if not exchange or not symbol or not ids.CODE_PATTERN.match(symbol):
                continue
            asset_class = "etf" if (record.get("assetType") or "").upper() == "ETF" else "equity"
            iid = ids.make(exchange, symbol)
            rows.append(instrument_row(iid, symbol, record.get("name") or symbol, asset_class, exchange, country="US", currency="USD",
                                       source="alpha_vantage_listing_status", class_source="alpha_vantage_asset_type", class_confidence=0.95))
            aliases += alias_rows(iid, strong=name_aliases(record.get("name") or ""), tickers=[symbol], source="alpha_vantage")
            mappings.append({"instrument_id": iid, "provider": self.name, "provider_symbol": symbol, "priority": 10})
        return rows, aliases, mappings

    def search(self, query: str) -> list[dict]:
        payload = http.json_or_raise(self._get("SYMBOL_SEARCH", {"function": "SYMBOL_SEARCH", "keywords": query}), self.name)
        self._check(payload, self.name)
        return [{"provider_symbol": m.get("1. symbol"), "name": m.get("2. name"), "type": m.get("3. type"), "region": m.get("4. region"),
                 "currency": m.get("8. currency")} for m in payload.get("bestMatches", [])]
