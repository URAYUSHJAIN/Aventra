"""Crypto providers.

Binance public REST (keyless): listing via exchangeInfo, daily OHLCV klines (1000/request) — primary.
CoinGecko: coin list (21k coins) and USD price+volume series (keyless: 365 days max; Demo key optional,
COINGECKO_DEMO_API_KEY, 100 calls/min, 10k/month per CoinGecko pricing). CoinGecko market_chart has no OHLC.
"""
from __future__ import annotations

import pandas as pd

from ml.instruments import ids
from ml.instruments.master import alias_rows, instrument_row
from ml.providers import http
from ml.providers.base import InstrumentNotSupported, MalformedResponse, Provider, ProviderCapability, Series

BINANCE = "https://api.binance.com/api/v3"
COINGECKO = "https://api.coingecko.com/api/v3"


class BinanceProvider(Provider):
    name = "binance"
    capability = ProviderCapability(asset_classes=("crypto",), exchanges=("BINANCE",), fields=("open", "high", "low", "close", "volume"),
                                    listing=True, rate_limit_per_minute=600,
                                    terms="Public market data; weight-based limits, 429 then IP ban 2 min–3 days (Binance docs). Jurisdiction terms not verified.")

    def history(self, instrument: dict, provider_symbol: str, start=None) -> Series:
        start_ms = int(pd.Timestamp(start or "2017-01-01", tz="UTC").timestamp() * 1000)
        rows = []
        for _ in range(12):                      # ≤ 12 pages × 1000 days
            response = http.request(self.name, "klines", f"{BINANCE}/klines", per_minute=self.capability.rate_limit_per_minute,
                                    params={"symbol": provider_symbol, "interval": "1d", "startTime": start_ms, "limit": 1000})
            payload = http.json_or_raise(response, self.name)
            if not response.ok:
                raise InstrumentNotSupported(f"Binance: {payload.get('msg', response.status_code)}", self.name)
            if not isinstance(payload, list):
                raise MalformedResponse("Binance klines payload is not a list.", self.name)
            if not payload:
                break
            try:
                rows += [{"timestamp": pd.Timestamp(int(k[0]), unit="ms", tz="UTC"), "open": float(k[1]), "high": float(k[2]), "low": float(k[3]),
                          "close": float(k[4]), "volume": float(k[5])} for k in payload]
            except (IndexError, TypeError, ValueError) as error:
                raise MalformedResponse("Binance kline rows could not be parsed.", self.name) from error
            if len(payload) < 1000:
                break
            start_ms = int(payload[-1][0]) + 86_400_000
        if not rows:
            raise InstrumentNotSupported("Binance returned no klines.", self.name)
        return Series(pd.DataFrame(rows).drop_duplicates("timestamp"), self.name, provider_symbol, instrument.get("currency"), "UTC",
                      meta={"endpoint": "klines 1d", "note": "the latest kline is the current (incomplete) UTC day"})

    def list_instruments(self):
        payload = http.json_or_raise(http.request(self.name, "exchangeInfo", f"{BINANCE}/exchangeInfo", per_minute=30), self.name)
        rows, aliases, mappings = [], [], []
        for item in payload.get("symbols", []):
            if item.get("status") != "TRADING" or not item.get("isSpotTradingAllowed", True):
                continue
            base, quote = item.get("baseAsset", ""), item.get("quoteAsset", "")
            code = f"{base}-{quote}"
            if not ids.CODE_PATTERN.match(code):
                continue
            iid = ids.make("CRYPTO", code)
            rows.append(instrument_row(iid, item["symbol"], f"{base} / {quote}", "crypto", "BINANCE", currency=quote, source="binance_exchange_info",
                                       class_source="binance_spot", class_confidence=1.0))
            aliases += alias_rows(iid, tickers=[base] if len(base) >= 3 else [], source="binance")
            mappings.append({"instrument_id": iid, "provider": self.name, "provider_symbol": item["symbol"], "priority": 10})
        return rows, aliases, mappings


class CoinGeckoProvider(Provider):
    name = "coingecko"
    capability = ProviderCapability(asset_classes=("crypto",), exchanges=("COINGECKO",), fields=("close", "volume"), max_history_days=365,
                                    listing=True, search=True, credential_env="COINGECKO_DEMO_API_KEY", credential_optional=True,
                                    rate_limit_per_minute=5,
                                    terms="Demo plan: key, 100 calls/min, 10k/month; keyless public access limited to 365 days of history (docs/06).")

    def _headers(self):
        key = self.credential()
        return {"x-cg-demo-api-key": key} if key else {}

    def _per_minute(self):
        return 30 if self.credential() else self.capability.rate_limit_per_minute

    def history(self, instrument: dict, provider_symbol: str, start=None) -> Series:
        response = http.request(self.name, "market_chart", f"{COINGECKO}/coins/{provider_symbol}/market_chart", per_minute=self._per_minute(),
                                params={"vs_currency": "usd", "days": "365", "interval": "daily"}, headers=self._headers())
        payload = http.json_or_raise(response, self.name)
        if not response.ok or "prices" not in payload:
            raise InstrumentNotSupported(f"CoinGecko: {str(payload)[:120]}", self.name)
        volumes = {int(ts): v for ts, v in payload.get("total_volumes", [])}
        frame = pd.DataFrame([{"timestamp": pd.Timestamp(int(ts), unit="ms", tz="UTC").normalize(), "close": float(price), "volume": volumes.get(int(ts))}
                              for ts, price in payload["prices"]]).drop_duplicates("timestamp", keep="first")
        return Series(frame, self.name, provider_symbol, "USD", "UTC", meta={"endpoint": "market_chart days=365", "note": "daily USD close; no OHLC"})

    def list_instruments(self):
        payload = http.json_or_raise(http.request(self.name, "coins/list", f"{COINGECKO}/coins/list", per_minute=self._per_minute(),
                                                  headers=self._headers(), timeout=60), self.name)
        rows, aliases, mappings = [], [], []
        for coin in payload if isinstance(payload, list) else []:
            coin_id, name, symbol = coin.get("id", ""), coin.get("name", ""), (coin.get("symbol") or "").upper()
            code = f"CG-{coin_id}"
            if not coin_id or not ids.CODE_PATTERN.match(code) or not symbol:
                continue
            iid = ids.make("CRYPTO", code)
            rows.append(instrument_row(iid, symbol[:64], name or coin_id, "crypto", "COINGECKO", currency="USD", source="coingecko_coins_list",
                                       class_source="coingecko", class_confidence=1.0, capabilities={"has_ohlc": False}))
            aliases += alias_rows(iid, strong=[name] if len(name) >= 3 else [], source="coingecko")
            mappings.append({"instrument_id": iid, "provider": self.name, "provider_symbol": coin_id, "priority": 10})
        return rows, aliases, mappings

    def search(self, query: str) -> list[dict]:
        payload = http.json_or_raise(http.request(self.name, "search", f"{COINGECKO}/search", per_minute=self._per_minute(), params={"query": query},
                                                  headers=self._headers()), self.name)
        return [{"id": c.get("id"), "name": c.get("name"), "symbol": c.get("symbol"), "market_cap_rank": c.get("market_cap_rank")} for c in payload.get("coins", [])]
