"""Intelligence endpoints (union of Final Plan §19 and ML Pipeline §33 paths; see docs/14_API_SPECIFICATION.md).

Path segments that start with AN-/EV- are anomaly/event IDs; anything else is a canonical instrument ID
(legacy bare NSE symbols such as RELIANCE still resolve to XNSE:RELIANCE).
"""
from flask import Blueprint, request

from backend.services import intelligence_service as svc
from backend.utils.responses import ApiError, int_arg, ok, require_instrument_id
from ml.data import store

intelligence_api = Blueprint("intelligence", __name__)


def _refresh() -> bool:
    return request.args.get("refresh", "").lower() in {"1", "true", "yes"}


def _result(raw: str) -> dict:
    return svc.get_intelligence(require_instrument_id(raw), refresh=_refresh())


@intelligence_api.get("/intelligence/<instrument_id>")
def intelligence(instrument_id: str):
    return ok(_result(instrument_id))


@intelligence_api.get("/fingerprint/<instrument_id>")
def fingerprint(instrument_id: str):
    return ok(svc.fingerprint_view(_result(instrument_id)))


@intelligence_api.get("/anomalies")
def anomalies():
    raw = request.args.get("instrument") or request.args.get("symbol")
    limit = int_arg(request.args.get("limit"), 50, 1, 500)
    if raw:
        iid = require_instrument_id(raw)
        return ok({"instrument_id": iid, "anomalies": [e["anomaly"] for e in _result(iid)["events"]][:limit]})
    return ok({"anomalies": store.list_anomalies(limit=limit)})


@intelligence_api.get("/anomalies/<anomaly_id>")
def anomaly_detail(anomaly_id: str):
    event = store.get_event_by("anomaly_id", anomaly_id)
    if event is None:
        raise ApiError("Anomaly not found.", 404, "NOT_FOUND")
    return ok(event["anomaly"])


@intelligence_api.get("/anomaly/<instrument_id>")
def anomaly_for_instrument(instrument_id: str):
    return ok(svc.anomaly_view(_result(instrument_id)))


@intelligence_api.post("/anomaly/detect")
def anomaly_detect():
    payload = request.get_json(silent=True)
    raw = (payload.get("instrument_id") or payload.get("symbol")) if isinstance(payload, dict) else None
    if not isinstance(raw, str):
        raise ApiError("A JSON body with an 'instrument_id' string is required.", 400)
    return ok(svc.anomaly_view(svc.get_intelligence(require_instrument_id(raw), refresh=True)))


@intelligence_api.get("/events")
def events():
    raw = request.args.get("instrument") or request.args.get("symbol")
    limit = int_arg(request.args.get("limit"), 50, 1, 500)
    if raw:
        iid = require_instrument_id(raw)
        return ok({"instrument_id": iid, "events": _result(iid)["events"][:limit]})
    return ok({"events": store.list_events(limit=limit)})


@intelligence_api.get("/events/<key>")
def event_detail(key: str):
    if key.upper().startswith("EV-"):
        event = store.get_event_by("event_id", key)
        if event is None:
            raise ApiError("Event not found.", 404, "NOT_FOUND")
        return ok(event)
    iid = require_instrument_id(key)
    return ok({"instrument_id": iid, "events": _result(iid)["events"]})


@intelligence_api.get("/risk/<instrument_id>")
def risk(instrument_id: str):
    return ok(svc.risk_view(_result(instrument_id)))


@intelligence_api.get("/evidence/<key>")
def evidence(key: str):
    event = store.get_event_by("anomaly_id", key) or store.get_event_by("event_id", key)
    if event is None:
        raise ApiError("No evidence chain found for that anomaly or event ID.", 404, "NOT_FOUND")
    return ok({"event_id": event["event_id"], "anomaly_id": event["anomaly"]["anomaly_id"], "trading_date": event["trading_date"],
               "risk": event["risk"], "evidence": event["evidence"], "explanation": event["explanation"]})
