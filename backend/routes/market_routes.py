from flask import Blueprint, request

from backend.services import market_service
from backend.utils.responses import ApiError, int_arg, ok, require_instrument_id
from ml.data import store
from ml.instruments import master

market_api = Blueprint("market", __name__)
MAX_BATCH = 25


@market_api.get("/market/snapshots")
def snapshots():
    raw = [part.strip() for part in (request.args.get("ids") or request.args.get("symbols") or "").split(",") if part.strip()]
    if not raw:
        raise ApiError("Provide ?ids=ID1,ID2 (e.g. XNSE:RELIANCE,CRYPTO:BTC-USDT).", 400)
    if len(raw) > MAX_BATCH:
        raise ApiError(f"At most {MAX_BATCH} instruments per request.", 400)
    return ok({"items": market_service.snapshots(raw)})


@market_api.get("/market/<instrument_id>")
def snapshot(instrument_id: str):
    return ok(market_service.snapshot(require_instrument_id(instrument_id)))


@market_api.get("/market/<instrument_id>/history")
def history(instrument_id: str):
    return ok(market_service.history(require_instrument_id(instrument_id), int_arg(request.args.get("limit"), 250, 1, 5000)))


@market_api.get("/watchlists/default")
def default_watchlist():
    items = master.ensure_default_watchlist()
    rows = store.instruments_by_ids(items)
    return ok({"name": "default", "items": [{"instrument_id": iid, **({k: rows[iid][k] for k in ("symbol", "name", "asset_class", "exchange", "currency")} if iid in rows else {"status": "not_in_master"})}
                                            for iid in items], "configured_by": "AVENTRA_DEFAULT_WATCHLIST"})
