"""Indian mutual funds (AMFI official list + mfapi.in NAV history), OpenFIGI identifier mapping, SEC US listing.

AMFI NAVAll.txt: official scheme list with the latest NAV (8 fields; NAV and date are the last two).
mfapi.in: community-run NAV history keyed by AMFI scheme codes (Phase 0: 5/5 latest NAVs matched AMFI).
OpenFIGI: free identifier mapping/classification (keyless 25 mapping req/min; filter/search 5/min).
SEC company_tickers_exchange.json: public U.S. government listing of issuers (listing only, never prices);
fair-access policy: ≤ 10 requests/s with a declared User-Agent (verified in Phase 0).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pandas as pd

from ml.instruments import ids
from ml.instruments.master import alias_rows, instrument_row, name_aliases
from ml.providers import http
from ml.providers.base import InstrumentNotSupported, MalformedResponse, Provider, ProviderCapability, Series

AMFI_NAV_ALL = "https://www.amfiindia.com/spages/NAVAll.txt"
MFAPI = "https://api.mfapi.in/mf"
OPENFIGI = "https://api.openfigi.com/v3"
SEC_TICKERS = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_EXCHANGES = {"Nasdaq": "XNAS", "NYSE": "XNYS", "CBOE": "BATS"}
STALE_NAV_DAYS = 30


class AmfiProvider(Provider):
    name = "amfi"
    capability = ProviderCapability(asset_classes=("mutual_fund",), exchanges=("AMFI",), fields=("value",), history=False, listing=True,
                                    rate_limit_per_minute=6, terms="Public AMFI files; website terms not reviewed (docs/06).",
                                    notes="Listing + latest NAV only; history comes from mfapi.in.")

    def list_instruments(self):
        response = http.request(self.name, "NAVAll", AMFI_NAV_ALL, per_minute=6, timeout=60, headers={"Accept": "text/plain"})
        lines = [line.split(";") for line in response.text.splitlines() if line.count(";") >= 5 and line.split(";")[0].strip().isdigit()]
        if not lines:
            raise MalformedResponse("AMFI NAVAll.txt contained no scheme rows.", self.name)
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=STALE_NAV_DAYS)
        rows, aliases, mappings = [], [], []
        for fields in lines:
            code, name, nav_date = fields[0].strip(), fields[3].strip(), fields[-1].strip()
            plan = " ".join(f.strip() for f in fields[4:-2] if f.strip() and f.strip() != "-")
            try:
                active = datetime.strptime(nav_date, "%d-%b-%Y").date() >= cutoff
            except ValueError:
                active = False
            iid = ids.make("MF-IN", code)
            full_name = f"{name} — {plan}" if plan else name
            isin = fields[1].strip() if len(fields[1].strip()) == 12 else None
            rows.append(instrument_row(iid, code, full_name, "mutual_fund", "AMFI", country="IN", currency="INR", isin=isin, status="listed" if active else "inactive",
                                       source="amfi_navall", class_source="amfi", class_confidence=1.0))
            aliases += alias_rows(iid, strong=[name], source="amfi")
            mappings += [{"instrument_id": iid, "provider": "mfapi", "provider_symbol": code, "priority": 10},
                         {"instrument_id": iid, "provider": self.name, "provider_symbol": code, "priority": 50}]
        return rows, aliases, mappings


class MfapiProvider(Provider):
    name = "mfapi"
    capability = ProviderCapability(asset_classes=("mutual_fund",), exchanges=("AMFI",), fields=("value",), rate_limit_per_minute=60,
                                    terms="Community-run, keyless, states no rate limit; terms page unavailable (docs/06). AMFI is authoritative.")

    def history(self, instrument: dict, provider_symbol: str, start=None) -> Series:
        response = http.request(self.name, "scheme", f"{MFAPI}/{provider_symbol}", per_minute=self.capability.rate_limit_per_minute)
        payload = http.json_or_raise(response, self.name)
        data = payload.get("data") if isinstance(payload, dict) else None
        if not response.ok or not data:
            raise InstrumentNotSupported("mfapi.in has no NAV history for this scheme.", self.name)
        try:
            frame = pd.DataFrame([{"timestamp": pd.Timestamp(datetime.strptime(row["date"], "%d-%m-%Y"), tz="UTC"), "value": float(row["nav"])} for row in data])
        except (KeyError, ValueError) as error:
            raise MalformedResponse("mfapi.in NAV rows could not be parsed.", self.name) from error
        frame = frame[frame["value"] > 0].drop_duplicates("timestamp")
        if start is not None:
            frame = frame[frame["timestamp"] >= pd.Timestamp(start, tz="UTC")]
        frame["close"] = frame["value"]
        return Series(frame, self.name, provider_symbol, "INR", "Asia/Kolkata", value_kind="nav",
                      meta={"scheme_name": (payload.get("meta") or {}).get("scheme_name"), "note": "NAV series (declared once per business day)"})


class OpenFigiProvider(Provider):
    name = "openfigi"
    capability = ProviderCapability(asset_classes=(), fields=(), history=False, search=True, credential_env="OPENFIGI_API_KEY", credential_optional=True,
                                    rate_limit_per_minute=20, terms="Free and open; keyless 25 mapping req/min (10 jobs), 5 search/filter req/min (docs/06).")

    def _headers(self):
        key = self.credential()
        return {"Content-Type": "application/json", **({"X-OPENFIGI-APIKEY": key} if key else {})}

    def map_isins(self, isins: list[str]) -> dict[str, list[dict]]:
        """ISIN → OpenFIGI records (securityType, securityType2, exchCode, ticker, name). Batches of 10 without a key."""
        batch = 100 if self.credential() else 10
        per_minute = 250 if self.credential() else 25
        out: dict[str, list[dict]] = {}
        for start in range(0, len(isins), batch):
            chunk = isins[start:start + batch]
            response = http.request(self.name, "mapping", f"{OPENFIGI}/mapping", per_minute=per_minute, method="POST",
                                    json_body=[{"idType": "ID_ISIN", "idValue": isin} for isin in chunk], headers=self._headers())
            payload = http.json_or_raise(response, self.name)
            if not isinstance(payload, list):
                raise MalformedResponse("OpenFIGI mapping response is not a list.", self.name)
            for isin, item in zip(chunk, payload):
                out[isin] = item.get("data", []) if isinstance(item, dict) else []
        return out


FIGI_CLASS = {"ETP": "etf", "REIT": "reit", "Common Stock": "equity", "Mutual Fund": "mutual_fund", "Index": "index"}


def refine_class_from_figi(records: list[dict], exch_code: str = "IN") -> tuple[str, float] | None:
    """securityType2/securityType of the listing on `exch_code` → Aventra class (None when not decisive)."""
    for record in records:
        if record.get("exchCode") == exch_code:
            for key in ("securityType", "securityType2"):
                value = record.get(key)
                if value in FIGI_CLASS:
                    return FIGI_CLASS[value], 0.95
    return None


def sec_user_agent() -> str:
    """SEC fair access asks for a User-Agent naming the organisation and a real contact address (AVENTRA_SEC_USER_AGENT)."""
    return os.getenv("AVENTRA_SEC_USER_AGENT", "").strip() or "Aventra B.Tech research prototype (ABES Engineering College; contact not configured)"


class SecListingProvider(Provider):
    name = "sec"
    capability = ProviderCapability(asset_classes=(), fields=(), history=False, listing=True, rate_limit_per_minute=300,
                                    terms="U.S. government public data; ≤ 10 requests/s with declared User-Agent (SEC fair access).",
                                    notes="Listing only: issuers on Nasdaq/NYSE/CBOE. Asset class is equity unless the name marks an ETF.")

    def list_instruments(self):
        response = http.request(self.name, "company_tickers_exchange", SEC_TICKERS, per_minute=60, timeout=60,
                                headers={"User-Agent": sec_user_agent()})
        payload = http.json_or_raise(response, self.name)
        fields = payload.get("fields") or []
        if fields[:4] != ["cik", "name", "ticker", "exchange"]:
            raise MalformedResponse("SEC ticker file has an unexpected layout.", self.name)
        rows, aliases, mappings = [], [], []
        for cik, name, ticker, exchange in (row[:4] for row in payload.get("data", [])):
            mic = SEC_EXCHANGES.get(exchange)
            ticker = (ticker or "").upper()
            if not mic or not ticker or not ids.CODE_PATTERN.match(ticker):
                continue
            is_etf = " ETF" in f" {name.upper()} " or name.upper().endswith(" ETF")
            iid = ids.make(mic, ticker)
            rows.append(instrument_row(iid, ticker, name, "etf" if is_etf else "equity", mic, country="US", currency="USD", source="sec_company_tickers",
                                       class_source="sec_name_rule", class_confidence=0.6))
            aliases += alias_rows(iid, strong=name_aliases(name), tickers=[ticker] if len(ticker) >= 3 else [], source="sec")
            mappings.append({"instrument_id": iid, "provider": "alpha_vantage", "provider_symbol": ticker, "priority": 10})
        return rows, aliases, mappings
