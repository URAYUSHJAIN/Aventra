"""Intelligence endpoints (union of Final Plan §19 and ML Pipeline §33 paths; see docs/14_API_SPECIFICATION.md).

Path segments that start with an ID prefix (AN-, EV-) are treated as IDs, anything else as a symbol.
"""
from flask import Blueprint, request

from backend.services import intelligence_service as svc
from backend.utils.responses import ApiError, int_arg, ok, require_symbol
from ml.data import store

intelligence_api = Blueprint("intelligence", __name__)


def _refresh() -> bool:
    return request.args.get("refresh", "").lower() in {"1", "true", "yes"}


def _result(symbol: str) -> dict:
    return svc.get_intelligence(require_symbol(symbol, analysed_only=True), refresh=_refresh())


@intelligence_api.get("/intelligence/<symbol>")
def intelligence(symbol: str):
    return ok(_result(symbol))


@intelligence_api.get("/fingerprint/<symbol>")
def fingerprint(symbol: str):
    return ok(svc.fingerprint_view(_result(symbol)))


@intelligence_api.get("/anomalies")
def anomalies():
    symbol = request.args.get("symbol")
    limit = int_arg(request.args.get("limit"), 50, 1, 500)
    if symbol:
        return ok({"symbol": require_symbol(symbol, analysed_only=True), "anomalies": [e["anomaly"] for e in _result(symbol)["events"]][:limit]})
    return ok({"anomalies": store.list_anomalies(limit=limit)})


@intelligence_api.get("/anomalies/<anomaly_id>")
def anomaly_detail(anomaly_id: str):
    event = store.get_event_by("anomaly_id", anomaly_id)
    if event is None:
        raise ApiError("Anomaly not found.", 404)
    return ok(event["anomaly"])


@intelligence_api.get("/anomaly/<symbol>")
def anomaly_for_symbol(symbol: str):
    return ok(svc.anomaly_view(_result(symbol)))


@intelligence_api.post("/anomaly/detect")
def anomaly_detect():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("symbol"), str):
        raise ApiError("A JSON body with a 'symbol' string is required.", 400)
    symbol = require_symbol(payload["symbol"], analysed_only=True)
    return ok(svc.anomaly_view(svc.get_intelligence(symbol, refresh=True)))


@intelligence_api.get("/events")
def events():
    symbol = request.args.get("symbol")
    limit = int_arg(request.args.get("limit"), 50, 1, 500)
    if symbol:
        return ok({"symbol": require_symbol(symbol, analysed_only=True), "events": _result(symbol)["events"][:limit]})
    return ok({"events": store.list_events(limit=limit)})


@intelligence_api.get("/events/<key>")
def event_detail(key: str):
    if key.upper().startswith("EV-"):
        event = store.get_event_by("event_id", key)
        if event is None:
            raise ApiError("Event not found.", 404)
        return ok(event)
    return ok({"symbol": require_symbol(key, analysed_only=True), "events": _result(key)["events"]})


@intelligence_api.get("/risk/<symbol>")
def risk(symbol: str):
    return ok(svc.risk_view(_result(symbol)))


@intelligence_api.get("/evidence/<key>")
def evidence(key: str):
    event = store.get_event_by("anomaly_id", key) or store.get_event_by("event_id", key)
    if event is None:
        raise ApiError("No evidence chain found for that anomaly or event ID.", 404)
    return ok({"event_id": event["event_id"], "anomaly_id": event["anomaly"]["anomaly_id"], "trading_date": event["trading_date"],
               "risk": event["risk"], "evidence": event["evidence"], "explanation": event["explanation"]})
