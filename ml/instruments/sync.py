"""Instrument Master synchronisation from listing providers (no top-N lists: every listed instrument is stored).

    py -3.12 -m ml.instruments.sync                  # all configured listing providers + enrichment
    py -3.12 -m ml.instruments.sync binance amfi     # selected providers
    py -3.12 -m ml.instruments.sync --refine 500     # OpenFIGI classification refinement for up to 500 ISINs
    py -3.12 -m ml.instruments.sync --import-nse EQUITY_L.csv   # manual import of an NSE file YOU downloaded

NSE website files are never downloaded automatically (NSE Terms of Use); --import-nse (master.import_nse_listing) takes a
file the user downloaded. Popularity (CoinGecko market-cap rank) only orders search results; it never limits them.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys

from ml.data import store
from ml.instruments.master import alias_rows
from ml.providers import registry
from ml.providers.base import ProviderError
from ml.providers.funds_and_reference import refine_class_from_figi

logger = logging.getLogger(__name__)
LISTING_ORDER = ("upstox", "sec", "alpha_vantage", "binance", "coingecko", "frankfurter", "amfi")
REFINED_SOURCE = "openfigi"
QUOTE_PREFERENCE = {"USDT": 0.1, "USDC": 0.2, "FDUSD": 0.3, "USD": 0.1, "INR": 0.4, "EUR": 0.5, "BTC": 0.6, "ETH": 0.7}


def sync_listing(provider_name: str) -> dict:
    provider = registry.get(provider_name)
    ok, reason = provider.listing_available()
    if not ok:
        store.record_listing_snapshot(provider_name, 0, None, "skipped", note=reason)
        return {"provider": provider_name, "status": "skipped", "reason": reason}
    try:
        rows, aliases, mappings = provider.list_instruments()
    except ProviderError as error:
        store.record_listing_snapshot(provider_name, 0, None, "failed", note=str(error)[:300])
        logger.warning("Listing sync failed for %s: %s", provider_name, error)
        return {"provider": provider_name, "status": "failed", "reason": getattr(error, "code", "PROVIDER_ERROR"), "detail": str(error)}
    refined = store.classifications(REFINED_SOURCE)
    for row in rows:   # an OpenFIGI refinement outranks a name/series rule from a later re-sync
        if row["instrument_id"] in refined:
            row["asset_class"], row["class_source"], row["class_confidence"] = refined[row["instrument_id"]]
    digest = getattr(provider, "last_listing_sha256", None) or hashlib.sha256(json.dumps([r["instrument_id"] for r in rows]).encode()).hexdigest()
    store.upsert_instruments(rows, aliases, mappings)
    store.record_listing_snapshot(provider_name, len(rows), digest, "ok")
    return {"provider": provider_name, "status": "ok", "instruments": len(rows)}


def enrich_crypto(pages: int = 4) -> dict:
    """CoinGecko market-cap ranks → popularity for coins, and coin names as aliases for Binance pairs whose base
    asset is the symbol of the highest-ranked coin (resolves e.g. 'bitcoin' → CRYPTO:BTC-USDT)."""
    from ml.providers import http
    provider = registry.get("coingecko")
    popularity, best_by_symbol = {}, {}
    for page in range(1, pages + 1):
        try:
            response = http.request("coingecko", "coins/markets", "https://api.coingecko.com/api/v3/coins/markets", per_minute=provider._per_minute(),
                                    params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": 250, "page": page}, headers=provider._headers())
            coins = http.json_or_raise(response, "coingecko") if response.ok else []
        except ProviderError as error:
            logger.warning("CoinGecko markets page %d failed: %s", page, error)
            break
        for coin in coins if isinstance(coins, list) else []:
            if coin.get("market_cap_rank"):
                popularity[f"CRYPTO:CG-{coin['id']}"] = float(coin["market_cap_rank"])
                best_by_symbol.setdefault((coin.get("symbol") or "").upper(), (coin["market_cap_rank"], coin.get("name")))
    store.set_popularity({iid: rank for iid, rank in popularity.items() if store.get_instrument(iid)})
    aliases, binance_popularity = [], {}
    with store.begin() as conn:
        from sqlalchemy import select
        from ml.data import db
        pairs = conn.execute(select(db.instruments.c.instrument_id).where(db.instruments.c.exchange == "BINANCE")).scalars().all()
    for iid in pairs:
        base = iid.split(":", 1)[1].split("-")[0].upper()
        if base in best_by_symbol:
            rank, name = best_by_symbol[base]
            aliases += alias_rows(iid, strong=[name] if name and len(name) >= 3 else [], source="coingecko_markets")
            # Ordering heuristic only: within one coin, USD-stablecoin quotes sort before other quote assets.
            quote = iid.rsplit("-", 1)[-1]
            binance_popularity[iid] = float(rank) + QUOTE_PREFERENCE.get(quote, 0.9)
    if aliases:
        store.upsert_instruments([], aliases)
    store.set_popularity(binance_popularity)
    return {"coins_ranked": len(popularity), "binance_pairs_named": len(binance_popularity)}


def refine_with_openfigi(limit: int = 250, exchange: str = "XNSE", exch_code: str = "IN") -> dict:
    """Map ISINs of rule-classified instruments through OpenFIGI and store decisive classes (ETF/REIT/equity)."""
    from sqlalchemy import and_, select
    from ml.data import db
    with db.get_engine().connect() as conn:
        rows = conn.execute(select(db.instruments.c.instrument_id, db.instruments.c.isin).where(and_(
            db.instruments.c.exchange == exchange, db.instruments.c.isin.isnot(None), db.instruments.c.asset_class.in_(["equity", "etf"]),
            db.instruments.c.class_source.notlike(f"{REFINED_SOURCE}%"))).limit(limit)).all()
    if not rows:
        return {"checked": 0, "changed": 0}
    try:
        mapped = registry.get("openfigi").map_isins([isin for _, isin in rows])
    except ProviderError as error:
        return {"checked": 0, "changed": 0, "error": str(error)}
    changed = 0
    for iid, isin in rows:
        decision = refine_class_from_figi(mapped.get(isin, []), exch_code)
        if decision:
            asset_class, confidence = decision
            store.set_instrument_fields(iid, asset_class=asset_class, class_source=f"{REFINED_SOURCE}:{asset_class}", class_confidence=confidence)
            changed += 1
        else:
            store.set_instrument_fields(iid, class_source=f"{REFINED_SOURCE}:undecided")
    return {"checked": len(rows), "changed": changed}


def sync_all(providers: list[str] | None = None) -> list[dict]:
    results = [sync_listing(name) for name in (providers or LISTING_ORDER)]
    if providers is None or {"binance", "coingecko"} & set(providers):
        results.append({"provider": "crypto_enrichment", **enrich_crypto()})
    return results


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from ml.data import migrate
    migrate.upgrade()
    if argv[:1] == ["--refine"]:
        print(refine_with_openfigi(int(argv[1]) if len(argv) > 1 else 250))
        return 0
    if argv[:1] == ["--import-nse"] and len(argv) == 2:
        from ml.instruments.master import import_nse_listing
        print(import_nse_listing(argv[1]))
        return 0
    for result in sync_all(argv or None):
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
