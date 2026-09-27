"""Provider registry, capability matrix and router.

The router selects legitimate providers for an instrument by asset class, exchange, credentials, health and the
instrument's provider mappings, then tries them in priority order. It never falls back to synthetic or
non-approved data: if every candidate fails, callers receive DataUnavailable with the per-provider reasons.
Yahoo Finance is not registered (Phase 0 decision, AGENTS.md C22).
"""
from __future__ import annotations

import logging
from dataclasses import asdict

from ml import config
from ml.providers import http
from ml.providers.alpha_vantage import AlphaVantageProvider
from ml.providers.base import InstrumentNotSupported, MalformedResponse, Provider, ProviderError, ProviderUnavailable, RateLimited, Series
from ml.providers.crypto import BinanceProvider, CoinGeckoProvider
from ml.providers.funds_and_reference import AmfiProvider, MfapiProvider, OpenFigiProvider, SecListingProvider
from ml.providers.reference_rates import EcbProvider, FredProvider, FrankfurterProvider
from ml.providers.upstox import UpstoxProvider

logger = logging.getLogger(__name__)


class DataUnavailable(RuntimeError):
    """No legitimate provider could supply the requested data. `code` is surfaced to the API/UI."""

    def __init__(self, message: str, code: str, attempts: list[dict]):
        super().__init__(message)
        self.code, self.attempts = code, attempts


def _build() -> dict[str, Provider]:
    providers: list[Provider] = [UpstoxProvider(), AlphaVantageProvider(), BinanceProvider(), CoinGeckoProvider(), FrankfurterProvider(), EcbProvider(),
                                 FredProvider(), MfapiProvider(), AmfiProvider(), OpenFigiProvider(), SecListingProvider()]
    if config.synthetic_test_data_enabled():
        from ml.providers.synthetic_test import SyntheticTestProvider
        providers.append(SyntheticTestProvider())
    return {p.name: p for p in providers}


def providers() -> dict[str, Provider]:
    return _build()   # cheap; re-evaluated so credentials/test flags set at runtime take effect


def get(name: str) -> Provider:
    return providers()[name]


def capability_matrix() -> list[dict]:
    out = []
    for provider in providers().values():
        ok, reason = provider.available()
        cap = asdict(provider.capability)
        cap["asset_classes"], cap["exchanges"], cap["fields"], cap["intervals"] = (list(cap[k]) for k in ("asset_classes", "exchanges", "fields", "intervals"))
        out.append({"provider": provider.name, "configured": ok, "unavailable_reason": reason, **cap, "health": http.health_snapshot(provider.name)})
    return out


def candidates(instrument: dict) -> list[tuple[Provider, str, int]]:
    """(provider, provider_symbol, priority) for history, in the order the router will try them."""
    registry = providers()
    ordered: list[tuple[Provider, str, int]] = []
    seen = set()
    for mapping in sorted(instrument.get("providers") or [], key=lambda m: m.get("priority", 100)):
        provider = registry.get(mapping["provider"])
        if provider and provider.capability.history and provider.supports(instrument):
            ordered.append((provider, mapping["provider_symbol"], mapping.get("priority", 100)))
            seen.add(provider.name)
    for provider in registry.values():   # providers that can derive a symbol without a stored mapping
        if provider.name in seen or not provider.capability.history or not provider.supports(instrument) or not hasattr(provider, "derive_symbol"):
            continue
        symbol = provider.derive_symbol(instrument)
        if symbol:
            ordered.append((provider, symbol, 200))
    return ordered


def fetch_history(instrument: dict, start=None) -> tuple[Series, list[dict]]:
    """Try legitimate providers in order. Returns (series, attempts) or raises DataUnavailable."""
    attempts: list[dict] = []
    options = candidates(instrument)
    if not options:
        raise DataUnavailable(f"No configured data provider covers {instrument.get('asset_class')} instruments on {instrument.get('exchange')}.",
                              "NO_PROVIDER_FOR_ASSET", attempts)
    for provider, symbol, _ in options:
        ok, reason = provider.available()
        if not ok:
            attempts.append({"provider": provider.name, "status": "PROVIDER_UNAVAILABLE", "reason": reason,
                             "detail": f"set {provider.capability.credential_env} to enable {provider.name}"})
            continue
        try:
            series = provider.history(instrument, symbol, start)
        except (ProviderUnavailable, RateLimited, InstrumentNotSupported, MalformedResponse, ProviderError) as error:
            attempts.append({"provider": provider.name, "status": getattr(error, "code", "PROVIDER_ERROR"), "reason": getattr(error, "reason", None),
                             "detail": str(error)[:200]})
            _mark(instrument, provider.name, False, str(error))
            continue
        if series.frame.empty:
            attempts.append({"provider": provider.name, "status": "INSUFFICIENT_SOURCE_DATA", "detail": "provider returned no observations"})
            continue
        attempts.append({"provider": provider.name, "status": "OK", "rows": int(len(series.frame))})
        _mark(instrument, provider.name, True)
        return series, attempts
    codes = {a["status"] for a in attempts}
    if codes <= {"INSTRUMENT_NOT_FOUND"}:
        code = "INSTRUMENT_NOT_FOUND"
    elif "RATE_LIMITED" in codes:
        code = "RATE_LIMITED"
    else:
        code = "PROVIDER_UNAVAILABLE"
    raise DataUnavailable("Data unavailable / insufficient source data: no legitimate provider returned data for this instrument.", code, attempts)


def _mark(instrument: dict, provider: str, ok: bool, error: str | None = None) -> None:
    try:
        from ml.data import store
        if instrument.get("instrument_id") and any(m["provider"] == provider for m in instrument.get("providers") or []):
            store.mark_provider_symbol(instrument["instrument_id"], provider, ok, error)
    except Exception:
        logger.debug("provider_symbols health update failed", exc_info=True)
