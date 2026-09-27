"""Instrument discovery: search is the primary entry point (GET /api/instruments/search)."""
from flask import Blueprint, request

from backend.utils.responses import ApiError, choice_arg, int_arg, ok, require_instrument_id
from ml.data import store
from ml.instruments import master
from ml.instruments.profiles import ASSET_CLASSES
from ml.providers import registry
from ml.providers.base import ProviderError

instrument_api = Blueprint("instruments", __name__)


@instrument_api.get("/instruments/search")
def search():
    query = (request.args.get("q") or "").strip()
    if not 1 <= len(query) <= 64:
        raise ApiError("Search query must be 1–64 characters.", 400)
    asset_class = choice_arg(request.args.get("asset_class"), set(ASSET_CLASSES), "asset_class")
    exchange = (request.args.get("exchange") or "").strip().upper() or None
    country = (request.args.get("country") or "").strip().upper()[:2] or None
    result = master.search(query, asset_class=asset_class, exchange=exchange, country=country,
                           limit=int_arg(request.args.get("limit"), 20, 1, 50), cursor=request.args.get("cursor"))
    total = store.count_instruments()
    return ok({**result, "query": query, "master_size": total,
               "master_status": "empty — run the listing sync (py -3.12 -m ml.instruments.sync)" if total == 0 else "ok"})


@instrument_api.post("/instruments/resolve")
def resolve():
    """Resolve a query that is not in the master via providers that can search (FRED series when configured)."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("query"), str) or not payload["query"].strip():
        raise ApiError("A JSON body with a 'query' string is required.", 400)
    query = payload["query"].strip()[:64]
    existing = master.search(query, limit=10)["items"]
    created, unavailable = [], []
    fred = registry.get("fred")
    if fred.available()[0]:
        try:
            for series in fred.search(query)[:10]:
                row, aliases, mapping = fred.instrument_from_series(series)
                store.upsert_instruments([row], aliases, [mapping])
                created.append(row["instrument_id"])
        except ProviderError as error:
            unavailable.append({"provider": "fred", "status": getattr(error, "code", "PROVIDER_ERROR"), "detail": str(error)[:160]})
    else:
        unavailable.append({"provider": "fred", "status": "PROVIDER_UNAVAILABLE", "detail": "set FRED_API_KEY to resolve interest-rate and commodity series"})
    return ok({"query": query, "existing": existing, "created": created, "providers": unavailable})


@instrument_api.get("/instruments/<instrument_id>")
def detail(instrument_id: str):
    iid = require_instrument_id(instrument_id)
    row = master.get(iid)
    if row is None:
        raise ApiError(f"{iid} is not in the Instrument Master.", 404, "INSTRUMENT_NOT_FOUND")
    candidates = [{"provider": p.name, "provider_symbol": symbol, "configured": p.available()[0], "reason": p.available()[1]}
                  for p, symbol, _ in registry.candidates(store.get_instrument(iid))]
    return ok({**row, "data_providers": candidates})


@instrument_api.get("/providers")
def providers():
    return ok({"providers": registry.capability_matrix()})
