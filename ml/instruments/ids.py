"""Canonical instrument IDs: `<NAMESPACE>:<CODE>`.

Namespaces
  XNSE, XBOM, XNAS, XNYS, XASE, ARCX, BATS, …  exchange MIC → equities, ETFs, REITs      XNSE:RELIANCE, XBOM:500325
  IDX       indices                                                                 IDX:NSE-NIFTY50
  FX        forex pair BASEQUOTE                                                    FX:USDINR
  CRYPTO    exchange pair BASE-QUOTE (Binance) or CG-<coingecko id> (USD series)    CRYPTO:BTC-USDT, CRYPTO:CG-bitcoin
  MF-IN     Indian mutual fund, AMFI scheme code                                    MF-IN:119551
  RATE      interest-rate / yield series (FRED id)                                  RATE:DGS10
  CMDTY     commodity spot series (FRED id)                                         CMDTY:DCOILWTICO

Raw ticker symbols are never the database identity. Every external string must pass `parse()` before it is
used in a query or a provider request.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

NAMESPACE_PATTERN = re.compile(r"^(X[A-Z]{3}|ARCX|BATS|OTCM|IDX|FX|CRYPTO|MF-IN|RATE|CMDTY|TEST)$")
# TEST: synthetic instruments used only by the automated test-suite (never registered outside tests).
CODE_PATTERN = re.compile(r"^[A-Za-z0-9&^._\-]{1,48}$")
MAX_LENGTH = 80

# Legacy bare symbols (v0.1 URLs such as /api/intelligence/RELIANCE) resolve to NSE listings.
LEGACY_DEFAULT_NAMESPACE = "XNSE"


class InvalidInstrumentId(ValueError):
    pass


@dataclass(frozen=True)
class InstrumentId:
    namespace: str
    code: str

    def __str__(self) -> str:
        return f"{self.namespace}:{self.code}"

    @property
    def is_exchange_listed(self) -> bool:
        return self.namespace.startswith("X") or self.namespace in {"ARCX", "BATS", "OTCM"}


def parse(raw: str, allow_legacy: bool = True) -> InstrumentId:
    """Validate and normalise an ID. Bare legacy symbols map to XNSE when `allow_legacy`."""
    if not isinstance(raw, str):
        raise InvalidInstrumentId("Instrument ID must be a string.")
    text = raw.strip()
    if not text or len(text) > MAX_LENGTH:
        raise InvalidInstrumentId("Instrument ID is empty or too long.")
    if ":" not in text:
        if not allow_legacy:
            raise InvalidInstrumentId("Instrument ID must look like NAMESPACE:CODE, e.g. XNSE:RELIANCE.")
        symbol = text.upper()
        symbol = symbol[:-3] if symbol.endswith(".NS") else symbol
        if not CODE_PATTERN.match(symbol):
            raise InvalidInstrumentId("Invalid symbol.")
        return InstrumentId(LEGACY_DEFAULT_NAMESPACE, symbol)
    namespace, _, code = text.partition(":")
    namespace = namespace.upper()
    if not NAMESPACE_PATTERN.match(namespace):
        raise InvalidInstrumentId(f"Unknown instrument namespace '{namespace}'.")
    if namespace not in {"CRYPTO"}:            # CoinGecko ids are lower-case and case-sensitive
        code = code.upper()
    if not CODE_PATTERN.match(code):
        raise InvalidInstrumentId("Invalid instrument code.")
    return InstrumentId(namespace, code)


def make(namespace: str, code: str) -> str:
    return str(parse(f"{namespace}:{code}", allow_legacy=False))


def safe_key(instrument_id: str) -> str:
    """ID fragment for derived keys (anomaly/event IDs): only [A-Za-z0-9_-]."""
    return re.sub(r"[^A-Za-z0-9\-]", "_", instrument_id)
