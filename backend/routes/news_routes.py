import logging
from flask import Blueprint, current_app, jsonify, request

from backend.services.news_analysis_service import FinBertUnavailable, InvalidNewsText, get_news_analysis_service
from backend.utils.responses import ApiError, int_arg, ok, require_instrument_id
from ml.data.store import now_iso
from ml.news.ingest import ingest_news
from ml.pipelines.intelligence import resolve_instrument

news_api = Blueprint("news", __name__)
logger = logging.getLogger(__name__)


@news_api.get("")
def list_news():
    """GET /api/news?instrument=XNSE:RELIANCE&limit=20 (legacy ?symbol= still accepted): instrument-linked news with FinBERT sentiment."""
    raw = request.args.get("instrument") or request.args.get("symbol")
    if not raw:
        raise ApiError("Provide ?instrument=<instrument ID>.", 400)
    return _news_for(require_instrument_id(raw), int_arg(request.args.get("limit"), 20, 1, 100))


@news_api.get("/<instrument_id>")
def news_for_instrument(instrument_id: str):
    """GET /api/news/<instrument_id> (ML Pipeline path); same payload as /api/news?instrument=."""
    return _news_for(require_instrument_id(instrument_id), int_arg(request.args.get("limit"), 20, 1, 100))


def _news_for(instrument_id: str, limit: int):
    report = ingest_news(instrument_id, resolve_instrument(instrument_id))
    items = [{"news_id": item["news_id"], "headline": item["headline"], "source": item.get("source"), "url": item.get("url"), "published_at": item["published_at"],
              "is_demo": item.get("is_demo", False), "sentiment": item.get("sentiment"),
              "entity": next((link for link in item.get("links", []) if link["instrument_id"] == instrument_id), None)} for item in report["items"][:limit]]
    meta = {key: report.get(key) for key in ("provider", "is_demo", "fetched_at", "status", "message", "sentiment_status", "duplicates_removed")}
    if meta["status"] == "ok" and not items:
        meta["status"] = "no_relevant_news"
    return ok({"instrument_id": instrument_id, "symbol": instrument_id.split(":", 1)[1], "data_source": meta, "items": items})


@news_api.post("/analyze")
def analyze_news():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(success=False, error="A JSON request body is required."), 400

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        return jsonify(success=False, error="News text is required."), 400
    if len(text) > current_app.config["MAX_NEWS_TEXT_LENGTH"]:
        return jsonify(success=False, error="News text exceeds the 12,000 character limit."), 413

    try:
        result = get_news_analysis_service().analyze(text)
        logger.info("FinBERT inference completed")
        probabilities = (result["positive_probability"], result["neutral_probability"], result["negative_probability"])
        # Additive fields only: the original label/probability/score fields are unchanged for existing consumers.
        result = {**result, "sentiment": result["label"], "confidence": result.get("confidence", max(probabilities)),
                  "model": result.get("model", "ProsusAI/finBERT"), "timestamp": now_iso(), "source": "user_input", "text": text.strip()}
        return jsonify(success=True, data=result)
    except InvalidNewsText as error:
        return jsonify(success=False, error=str(error)), 400
    except FinBertUnavailable:
        logger.warning("FinBERT analysis requested while the model is unavailable")
        return jsonify(success=False, error="News analysis service is currently unavailable."), 503
    except Exception:
        logger.exception("FinBERT inference failed")
        return jsonify(success=False, error="Unable to analyse the text. Please try again."), 500
