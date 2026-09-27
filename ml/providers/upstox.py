"""Upstox — Indian markets (NSE/BSE equities, ETFs, REITs, InvITs, government/corporate bonds, indices).

Listing: the public instrument master file (no login). History: v3 historical candles, which the documentation
says require `Authorization: Bearer <token>` (UPSTOX_ACCESS_TOKEN; Upstox tokens expire daily). Phase 0: Upstox
staff approved personal use only — suitable for a local, single-user deployment with the user's own account.
MCX/NSE derivatives are not listed (expiring contracts; no continuous series is built).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from datetime import date, timedelta

import pandas as pd

from ml.data.calendars import session_open_utc
from ml.instruments import ids
from ml.instruments.master import alias_rows, instrument_row, name_aliases
from ml.providers import http
from ml.providers.base import InstrumentNotSupported, MalformedResponse, Provider, ProviderCapability, Series

INSTRUMENT_FILE = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
API = "https://api.upstox.com/v3/historical-candle"
NSE_EQUITY_SERIES = {"EQ", "BE", "BZ", "SM", "ST"}
NSE_BOND_SERIES = {"GS", "SG", "TB", "GB"} | {f"N{i}" for i in range(10)}
BSE_BOND_GROUPS = {"F", "G"}
ETF_NAME = re.compile(r"\bETF\b|BEES$", re.IGNORECASE)


def classify(segment: str, instrument_type: str, name: str, symbol: str) -> tuple[str, float, str]:
    """(asset_class, confidence, rule) from Upstox segment/series. ETFs share series EQ, so they are named-based."""
    kind = (instrument_type or "").upper()
    if segment == "NSE_EQ":
        if kind == "RR":
            return "reit", 0.95, "nse_series_RR"
        if kind == "IV":
            return "invit", 0.95, "nse_series_IV"
        if kind in NSE_BOND_SERIES or re.match(r"^N[0-9A-Z]$", kind):
            return "bond", 0.9, f"nse_series_{kind}"
        if kind in NSE_EQUITY_SERIES:
            if ETF_NAME.search(name) or ETF_NAME.search(symbol):
                return "etf", 0.8, "name_rule_etf"
            return "equity", 0.9, f"nse_series_{kind}"
        return "equity", 0.5, f"nse_series_{kind}_unmapped"
    if segment == "BSE_EQ":
        if kind in BSE_BOND_GROUPS:
            return "bond", 0.85, f"bse_group_{kind}"
        if re.search(r"\bREIT\b", name, re.IGNORECASE):
            return "reit", 0.8, "name_rule_reit"
        if re.search(r"\bINVIT\b", name, re.IGNORECASE):
            return "invit", 0.8, "name_rule_invit"
        if ETF_NAME.search(name):
            return "etf", 0.8, "name_rule_etf"
        return "equity", 0.8, f"bse_group_{kind}"
    return "index", 0.95, "segment_index"


def _slug(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text.upper())[:40]


class UpstoxProvider(Provider):
    name = "upstox"
    capability = ProviderCapability(
        asset_classes=("equity", "etf", "reit", "invit", "bond", "index"), exchanges=("XNSE", "XBOM", "NSE_INDEX", "BSE_INDEX"),
        fields=("open", "high", "low", "close", "volume"), listing=True, credential_env="UPSTOX_ACCESS_TOKEN", rate_limit_per_minute=300,
        terms="Personal use only (Upstox staff); documented limits 50/s, 500/min, 2000/30 min per user (docs/06).",
        notes="Instrument file is public; candles need a daily access token.",
    )

    def listing_available(self):
        return True, None   # the instrument master file is public; only candles need UPSTOX_ACCESS_TOKEN

    def history(self, instrument: dict, provider_symbol: str, start=None) -> Series:
        self.require_available()
        today = date.today()
        first = pd.Timestamp(start).date() if start is not None else today - timedelta(days=365 * 5)
        headers = {"Authorization": f"Bearer {self.credential()}"}
        candles, cursor = [], today
        while cursor > first:                      # one request per year of daily candles
            chunk_start = max(first, cursor - timedelta(days=364))
            url = f"{API}/{provider_symbol.replace('|', '%7C')}/days/1/{cursor.isoformat()}/{chunk_start.isoformat()}"
            response = http.request(self.name, "historical-candle", url, per_minute=self.capability.rate_limit_per_minute, headers=headers)
            payload = http.json_or_raise(response, self.name)
            if response.status_code == 401:
                raise InstrumentNotSupported("Upstox rejected the access token (expired or invalid).", self.name)
            if not response.ok or payload.get("status") != "success":
                message = (payload.get("errors") or [{}])[0].get("message", response.text[:120])
                raise InstrumentNotSupported(f"Upstox: {message}", self.name)
            candles.extend(payload.get("data", {}).get("candles", []))
            cursor = chunk_start - timedelta(days=1)
        if not candles:
            raise InstrumentNotSupported("Upstox returned no candles for this instrument.", self.name)
        calendar = instrument.get("calendar_code")
        try:
            frame = pd.DataFrame([{"timestamp": session_open_utc(pd.Timestamp(c[0]).date(), calendar), "open": float(c[1]), "high": float(c[2]),
                                   "low": float(c[3]), "close": float(c[4]), "volume": float(c[5])} for c in candles])
        except (IndexError, TypeError, ValueError) as error:
            raise MalformedResponse("Upstox candle rows could not be parsed.", self.name) from error
        frame = frame.drop_duplicates("timestamp")
        return Series(frame, self.name, provider_symbol, instrument.get("currency") or "INR", instrument.get("timezone"), adjusted=False,
                      meta={"endpoint": "v3/historical-candle days/1"})

    def list_instruments(self):
        response = http.request(self.name, "instrument-file", INSTRUMENT_FILE, per_minute=6, timeout=60)
        try:
            data = json.loads(gzip.decompress(response.content))
        except (OSError, ValueError) as error:
            raise MalformedResponse("Upstox instrument file could not be decoded.", self.name) from error
        self.last_listing_sha256 = hashlib.sha256(response.content).hexdigest()
        rows, aliases, mappings = [], [], []
        for item in data:
            segment = item.get("segment")
            if segment not in {"NSE_EQ", "BSE_EQ", "NSE_INDEX", "BSE_INDEX"}:
                continue
            symbol = (item.get("trading_symbol") or "").strip().upper()
            name = (item.get("name") or symbol).strip()
            if segment == "NSE_EQ":
                namespace, code, exchange = "XNSE", symbol, "XNSE"
            elif segment == "BSE_EQ":
                namespace, code, exchange = "XBOM", str(item.get("exchange_token") or ""), "XBOM"
            else:
                namespace, code, exchange = "IDX", f"{segment[:3]}-{_slug(symbol)}", segment
            # Only the canonical code must match the ID pattern; display symbols may contain spaces (e.g. "NIFTY 50").
            if not code or not symbol or not ids.CODE_PATTERN.match(code):
                continue
            asset_class, confidence, rule = classify(segment, item.get("instrument_type"), name, symbol)
            iid = ids.make(namespace, code)
            rows.append(instrument_row(iid, symbol, name, asset_class, exchange, country="IN", currency="INR", isin=item.get("isin"),
                                       source="upstox_instrument_file", class_source=f"upstox:{rule}", class_confidence=confidence))
            aliases += alias_rows(iid, strong=name_aliases(name), tickers=[symbol] if len(symbol) >= 3 else [], source="upstox")
            mappings.append({"instrument_id": iid, "provider": self.name, "provider_symbol": item["instrument_key"], "priority": 10})
        return rows, aliases, mappings
