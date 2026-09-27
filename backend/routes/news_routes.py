import logging
from flask import Blueprint, current_app, jsonify, request

from backend.services.news_analysis_service import FinBertUnavailable, InvalidNewsText, get_news_analysis_service
from backend.utils.responses import int_arg, ok, require_symbol
from ml.data.assets import get_asset
from ml.data.store import now_iso
from ml.news.ingest import ingest_news

news_api = Blueprint("news", __name__)
logger = logging.getLogger(__name__)


@news_api.get("")
def list_news():
    """GET /api/news?symbol=RELIANCE&limit=20 — asset-linked news with FinBERT sentiment."""
    symbol = require_symbol(request.args.get("symbol"), analysed_only=True)
    return _news_for(symbol, int_arg(request.args.get("limit"), 20, 1, 100))


@news_api.get("/<symbol>")
def news_for_symbol(symbol: str):
    """GET /api/news/<symbol> — ML Pipeline §33 path; same payload as /api/news?symbol=."""
    return _news_for(require_symbol(symbol, analysed_only=True), int_arg(request.args.get("limit"), 20, 1, 100))


def _news_for(symbol: str, limit: int):
    report = ingest_news(symbol, get_asset(symbol))
    items = [{"news_id": item["news_id"], "headline": item["headline"], "source": item.get("source"), "url": item.get("url"), "published_at": item["published_at"],
              "is_demo": item.get("is_demo", False), "sentiment": item.get("sentiment"),
              "entity": next((link for link in item.get("links", []) if link["symbol"] == symbol), None)} for item in report["items"][:limit]]
    meta = {key: report.get(key) for key in ("provider", "is_demo", "fetched_at", "status", "message", "sentiment_status", "duplicates_removed")}
    return ok({"symbol": symbol, "data_source": meta, "items": items})


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
