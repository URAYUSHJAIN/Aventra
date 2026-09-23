import logging
from flask import Blueprint, current_app, jsonify, request

from backend.services.news_analysis_service import FinBertUnavailable, InvalidNewsText, get_news_analysis_service

news_api = Blueprint("news", __name__)
logger = logging.getLogger(__name__)


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
        return jsonify(success=True, data=result)
    except InvalidNewsText as error:
        return jsonify(success=False, error=str(error)), 400
    except FinBertUnavailable:
        logger.warning("FinBERT analysis requested while the model is unavailable")
        return jsonify(success=False, error="News analysis service is currently unavailable."), 503
    except Exception:
        logger.exception("FinBERT inference failed")
        return jsonify(success=False, error="Unable to analyse the text. Please try again."), 500
