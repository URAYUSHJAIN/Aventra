"""Forex reference rates and FRED series.

Frankfurter (keyless; ECB and central-bank reference rates, daily) is primary for FX; the ECB Data Portal (keyless,
official EXR series, X per EUR) is the legitimate fallback, crossing two EUR rates when neither side is EUR.
FRED (FRED_API_KEY required; attribution notice mandatory; some series third-party copyrighted) serves interest
rates/yields (RATE:) and commodity spot series (CMDTY:). Reference rates are close-only: no OHLC, no volume.
"""
from __future__ import annotations

import io
import itertools
from datetime import date, timedelta

import pandas as pd

from ml.instruments import ids
from ml.instruments.master import alias_rows, instrument_row
from ml.providers import http
from ml.providers.base import InstrumentNotSupported, MalformedResponse, Provider, ProviderCapability, Series

FRANKFURTER = "https://api.frankfurter.dev/v1"
ECB = "https://data-api.ecb.europa.eu/service/data/EXR"
FRED = "https://api.stlouisfed.org/fred"
FRED_ATTRIBUTION = "This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis."


def _split_pair(provider_symbol: str) -> tuple[str, str]:
    if len(provider_symbol) != 6 or not provider_symbol.isalpha():
        raise InstrumentNotSupported(f"Not a currency pair: {provider_symbol}", "fx")
    return provider_symbol[:3].upper(), provider_symbol[3:].upper()


class FrankfurterProvider(Provider):
    name = "frankfurter"
    capability = ProviderCapability(asset_classes=("forex",), fields=("value",), listing=True, rate_limit_per_minute=60,
                                    terms="Keyless; throttled, no caps; data under each central bank's terms (docs/06).")

    def history(self, instrument: dict, provider_symbol: str, start=None) -> Series:
        base, quote = _split_pair(provider_symbol)
        first = pd.Timestamp(start).date() if start is not None else date.today() - timedelta(days=365 * 5)
        response = http.request(self.name, "timeseries", f"{FRANKFURTER}/{first.isoformat()}..", per_minute=self.capability.rate_limit_per_minute,
                                params={"base": base, "symbols": quote})
        payload = http.json_or_raise(response, self.name)
        if not response.ok or "rates" not in payload:
            raise InstrumentNotSupported(f"Frankfurter: {payload.get('message', response.status_code)}", self.name)
        frame = pd.DataFrame([{"timestamp": pd.Timestamp(day, tz="UTC"), "value": float(rates[quote])} for day, rates in payload["rates"].items() if quote in rates])
        if frame.empty:
            raise InstrumentNotSupported("Frankfurter returned no rates for this pair.", self.name)
        frame["close"] = frame["value"]
        return Series(frame, self.name, provider_symbol, quote, "UTC", value_kind="reference_rate",
                      meta={"endpoint": "v1 timeseries", "note": "ECB reference date; daily reference rate, not a traded OHLC bar"})

    def list_instruments(self):
        payload = http.json_or_raise(http.request(self.name, "currencies", f"{FRANKFURTER}/currencies", per_minute=30), self.name)
        if not isinstance(payload, dict) or not payload:
            raise MalformedResponse("Frankfurter currency list is empty.", self.name)
        rows, aliases, mappings = [], [], []
        for base, quote in itertools.permutations(sorted(payload), 2):
            code = f"{base}{quote}"
            iid = ids.make("FX", code)
            name = f"{payload[base]} / {payload[quote]} ({base}/{quote})"
            rows.append(instrument_row(iid, code, name, "forex", "FX", currency=quote, source="frankfurter_currencies", class_source="frankfurter", class_confidence=1.0))
            aliases += alias_rows(iid, strong=[f"{base}/{quote}", f"{base} {quote}"], source="frankfurter")
            mappings += [{"instrument_id": iid, "provider": self.name, "provider_symbol": code, "priority": 10},
                         {"instrument_id": iid, "provider": "ecb", "provider_symbol": code, "priority": 20}]
        return rows, aliases, mappings


class EcbProvider(Provider):
    name = "ecb"
    capability = ProviderCapability(asset_classes=("forex",), fields=("value",), rate_limit_per_minute=30,
                                    terms="Official ECB Data Portal (keyless); usage terms not reviewed (docs/06).")

    def _eur_series(self, currency: str, first: date) -> pd.Series:
        response = http.request(self.name, "EXR", f"{ECB}/D.{currency}.EUR.SP00.A", per_minute=self.capability.rate_limit_per_minute,
                                params={"format": "csvdata", "startPeriod": first.isoformat()}, headers={"Accept": "text/csv"})
        if not response.ok:
            raise InstrumentNotSupported(f"ECB has no EXR series for {currency}.", self.name)
        frame = pd.read_csv(io.StringIO(response.text))
        if not {"TIME_PERIOD", "OBS_VALUE"} <= set(frame.columns):
            raise MalformedResponse("ECB CSV is missing TIME_PERIOD/OBS_VALUE.", self.name)
        return frame.set_index(pd.to_datetime(frame["TIME_PERIOD"], utc=True))["OBS_VALUE"].astype(float)

    def history(self, instrument: dict, provider_symbol: str, start=None) -> Series:
        base, quote = _split_pair(provider_symbol)
        first = pd.Timestamp(start).date() if start is not None else date.today() - timedelta(days=365 * 5)
        per_eur_quote = pd.Series(1.0, index=[]) if quote == "EUR" else self._eur_series(quote, first)
        per_eur_base = pd.Series(1.0, index=[]) if base == "EUR" else self._eur_series(base, first)
        if base == "EUR":
            rate = per_eur_quote
        elif quote == "EUR":
            rate = 1.0 / per_eur_base
        else:
            rate = (per_eur_quote / per_eur_base).dropna()   # cross rate from two genuine EUR reference rates
        frame = pd.DataFrame({"timestamp": rate.index, "value": rate.values})
        frame["close"] = frame["value"]
        return Series(frame, self.name, provider_symbol, quote, "UTC", value_kind="reference_rate",
                      meta={"endpoint": "EXR D.*.EUR.SP00.A", "derivation": "direct" if "EUR" in (base, quote) else "cross via EUR reference rates"})


class FredProvider(Provider):
    name = "fred"
    capability = ProviderCapability(asset_classes=("rate", "commodity"), fields=("value",), search=True, credential_env="FRED_API_KEY",
                                    rate_limit_per_minute=60, terms=f"Free key required; attribution notice mandatory: “{FRED_ATTRIBUTION}”")

    def _get(self, endpoint: str, params: dict):
        self.require_available()
        response = http.request(self.name, endpoint, f"{FRED}/{endpoint}", per_minute=self.capability.rate_limit_per_minute,
                                params={**params, "api_key": self.credential(), "file_type": "json"})
        payload = http.json_or_raise(response, self.name)
        if not response.ok:
            raise InstrumentNotSupported(f"FRED: {payload.get('error_message', response.status_code)}", self.name)
        return payload

    def history(self, instrument: dict, provider_symbol: str, start=None) -> Series:
        params = {"series_id": provider_symbol}
        if start is not None:
            params["observation_start"] = pd.Timestamp(start).date().isoformat()
        payload = self._get("series/observations", params)
        rows = [{"timestamp": pd.Timestamp(o["date"], tz="UTC"), "value": float(o["value"])} for o in payload.get("observations", []) if o.get("value") not in (".", None)]
        if not rows:
            raise InstrumentNotSupported("FRED returned no observations.", self.name)
        frame = pd.DataFrame(rows)
        frame["close"] = frame["value"]
        return Series(frame, self.name, provider_symbol, instrument.get("currency"), "UTC", value_kind=instrument.get("capabilities", {}).get("value_kind", "yield"),
                      meta={"attribution": FRED_ATTRIBUTION})

    def search(self, query: str) -> list[dict]:
        payload = self._get("series/search", {"search_text": query, "limit": 20, "filter_variable": "frequency", "filter_value": "Daily"})
        return payload.get("seriess", [])

    @staticmethod
    def instrument_from_series(series: dict) -> tuple[dict, list[dict], dict]:
        units = (series.get("units") or "").lower()
        asset_class, namespace = ("rate", "RATE") if "percent" in units else ("commodity", "CMDTY")
        iid = ids.make(namespace, series["id"])
        row = instrument_row(iid, series["id"], series.get("title", series["id"]), asset_class, "FRED", country="US",
                             currency=None if asset_class == "rate" else "USD", source="fred_search", class_source="fred_units", class_confidence=0.8,
                             status="resolved", capabilities={"value_kind": "yield" if asset_class == "rate" else "price"})
        return row, alias_rows(iid, strong=[series.get("title", "")], source="fred"), {"instrument_id": iid, "provider": "fred", "provider_symbol": series["id"], "priority": 10}
