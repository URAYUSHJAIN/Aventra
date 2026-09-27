"""Provider interface, capability declaration, normalised series and typed errors."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

SERIES_COLUMNS = ["timestamp", "open", "high", "low", "close", "adj_close", "volume", "value"]


class ProviderError(RuntimeError):
    """Base class. `code` is the machine-readable state surfaced by the API."""
    code = "PROVIDER_ERROR"

    def __init__(self, message: str, provider: str = ""):
        super().__init__(message)
        self.provider = provider


class ProviderUnavailable(ProviderError):
    """Missing credentials, circuit open, network failure or provider down."""
    code = "PROVIDER_UNAVAILABLE"

    def __init__(self, message: str, provider: str = "", reason: str = "unavailable"):
        super().__init__(message, provider)
        self.reason = reason      # missing_credentials | circuit_open | network | http_error | budget_exhausted


class RateLimited(ProviderUnavailable):
    code = "RATE_LIMITED"

    def __init__(self, message: str, provider: str = "", retry_after: float | None = None):
        super().__init__(message, provider, reason="rate_limited")
        self.retry_after = retry_after


class InstrumentNotSupported(ProviderError):
    """The provider has no data for this instrument (unknown symbol, delisted, wrong class)."""
    code = "INSTRUMENT_NOT_FOUND"


class MalformedResponse(ProviderError):
    code = "MALFORMED_PROVIDER_RESPONSE"


@dataclass(frozen=True)
class ProviderCapability:
    """What a provider can serve. Used by the router and exposed as the capability matrix (GET /api/providers)."""
    asset_classes: tuple[str, ...]
    exchanges: tuple[str, ...] = ()               # empty = any exchange of the listed classes
    fields: tuple[str, ...] = ("close",)          # subset of open, high, low, close, volume, value
    intervals: tuple[str, ...] = ("1d",)
    max_history_days: int | None = None           # None = provider's full history
    history: bool = True
    listing: bool = False                         # can enumerate instruments for the master
    search: bool = False
    credential_env: str | None = None             # env var that must be set, or None
    credential_optional: bool = False             # works without the credential (with lower limits)
    rate_limit_per_minute: float = 60.0
    daily_budget: int | None = None
    terms: str = ""                               # summary of the verified terms (docs/06)
    notes: str = ""


@dataclass
class Series:
    """Normalised observations for one instrument from one provider. Timestamps are UTC bar starts."""
    frame: pd.DataFrame
    provider: str
    provider_symbol: str
    currency: str | None
    timezone: str | None
    interval: str = "1d"
    adjusted: bool = False
    value_kind: str = "price"
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        for column in SERIES_COLUMNS:
            if column not in self.frame.columns:
                self.frame[column] = float("nan")
        self.frame = self.frame[SERIES_COLUMNS].sort_values("timestamp").reset_index(drop=True)


class Provider:
    name = "base"
    capability = ProviderCapability(asset_classes=())

    def available(self) -> tuple[bool, str | None]:
        """(True, None) or (False, reason). Missing mandatory credentials are reported, never raised at import."""
        cap = self.capability
        if cap.credential_env and not cap.credential_optional and not os.getenv(cap.credential_env, "").strip():
            return False, "missing_credentials"
        return True, None

    def listing_available(self) -> tuple[bool, str | None]:
        """Listing may need different credentials than history (e.g. Upstox's instrument file is public)."""
        return self.available()

    def credential(self) -> str | None:
        env = self.capability.credential_env
        value = os.getenv(env, "").strip() if env else ""
        return value or None

    def require_available(self) -> None:
        ok, reason = self.available()
        if not ok:
            raise ProviderUnavailable(f"{self.name} is not configured ({self.capability.credential_env} is not set).", self.name, reason=reason or "unavailable")

    def supports(self, instrument: dict) -> bool:
        cap = self.capability
        if instrument.get("asset_class") not in cap.asset_classes:
            return False
        return not cap.exchanges or instrument.get("exchange") in cap.exchanges

    def provider_symbol(self, instrument: dict) -> str | None:
        """Provider-specific symbol from the master mapping (provider_symbols table)."""
        for mapping in instrument.get("providers") or []:
            if mapping["provider"] == self.name:
                return mapping["provider_symbol"]
        return None

    def history(self, instrument: dict, provider_symbol: str, start: date | None = None) -> Series:
        raise NotImplementedError

    def list_instruments(self) -> tuple[list[dict], list[dict], list[dict]]:
        """(instrument rows, alias rows, provider_symbol rows) for the Instrument Master. Listing providers only."""
        raise NotImplementedError

    def search(self, query: str) -> list[dict]:
        raise NotImplementedError
