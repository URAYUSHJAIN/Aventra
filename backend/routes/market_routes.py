from flask import Blueprint, request

from backend.services import market_service
from backend.utils.responses import ApiError, int_arg, ok, require_symbol
from ml.data.assets import all_assets, benchmark

market_api = Blueprint("market", __name__)
MAX_BATCH = 25


@market_api.get("/assets")
def assets():
    return ok({"assets": [asset.to_dict() for asset in all_assets()], "benchmark": benchmark()})


@market_api.get("/market/quotes")
def quotes():
    raw = [part for part in (request.args.get("symbols") or "").split(",") if part.strip()]
    if not raw:
        raise ApiError("Provide ?symbols=SYM1,SYM2.", 400)
    if len(raw) > MAX_BATCH:
        raise ApiError(f"At most {MAX_BATCH} symbols per request.", 400)
    return ok({"quotes": market_service.get_quotes([require_symbol(item) for item in raw])})


@market_api.get("/market/search")
def search():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2 or len(query) > 40:
        raise ApiError("Search query must be 2–40 characters.", 400)
    return ok({"results": market_service.search(query)})


@market_api.get("/market/<symbol>")
def quote(symbol: str):
    return ok(market_service.get_quote(require_symbol(symbol)))


@market_api.get("/market/<symbol>/history")
def history(symbol: str):
    limit = int_arg(request.args.get("limit"), 250, 1, 2000)
    return ok(market_service.get_history(require_symbol(symbol, analysed_only=True), limit))
