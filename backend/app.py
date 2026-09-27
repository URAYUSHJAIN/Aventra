import logging
import os
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from backend.routes.intelligence_routes import intelligence_api
from backend.routes.market_routes import market_api
from backend.routes.news_routes import news_api
from backend.utils.responses import ApiError
from ml import config as ml_config
from ml.data.market_providers import ProviderError
from ml.data.validation import MarketDataError
from ml.news.finbert import DEFAULT_MODEL_PATH
from ml.pipelines.intelligence import InsufficientHistory, UnknownAsset

logger = logging.getLogger(__name__)


def create_app(test_config=None):
    app = Flask(__name__)
    configured_origins = os.getenv("CORS_ORIGINS", "*")
    origins = "*" if configured_origins == "*" else [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    app.config.from_mapping(MAX_NEWS_TEXT_LENGTH=12000, CORS_ORIGINS=origins)
    if test_config:
        app.config.update(test_config)

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    app.register_blueprint(news_api, url_prefix="/api/news")
    app.register_blueprint(market_api, url_prefix="/api")
    app.register_blueprint(intelligence_api, url_prefix="/api")
    _register_error_handlers(app)

    @app.get("/api/health")
    def health():
        model_path = os.getenv("FINBERT_MODEL_PATH", str(DEFAULT_MODEL_PATH))
        return jsonify(success=True, data={
            "status": "ok",
            "data_mode": ml_config.data_mode(),
            "finbert_model_files": "present" if os.path.isfile(os.path.join(model_path, "pytorch_model.bin")) else "missing",
            "demo_dataset": "present" if (ml_config.DEMO_DIR / "market.csv").is_file() else "missing",
            "pipeline_version": ml_config.PIPELINE_VERSION,
        })

    return app


def _register_error_handlers(app: Flask) -> None:
    """Map domain exceptions to the {success: false, error} envelope. Messages are safe for users; stack traces are only logged."""

    @app.errorhandler(ApiError)
    def api_error(error: ApiError):
        return jsonify(success=False, error=error.message), error.status

    @app.errorhandler(UnknownAsset)
    def unknown_asset(error):
        return jsonify(success=False, error=str(error)), 404

    @app.errorhandler(InsufficientHistory)
    def insufficient_history(error):
        return jsonify(success=False, error=str(error), status="insufficient_history"), 422

    @app.errorhandler(ProviderError)
    def provider_error(error: ProviderError):
        if error.kind == "not_found":
            return jsonify(success=False, error=str(error)), 404
        logger.warning("Upstream provider failure: %s", error)
        return jsonify(success=False, error="The market data provider is currently unavailable. Please try again later."), 502

    @app.errorhandler(MarketDataError)
    def market_data_error(error):
        return jsonify(success=False, error="Market data from the provider could not be validated."), 502

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        return jsonify(success=False, error=error.description or error.name), error.code

    @app.errorhandler(Exception)
    def unexpected(error):
        logger.exception("Unhandled API error")
        return jsonify(success=False, error="An unexpected error occurred. Please try again."), 500


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Local development server only; containers use gunicorn with debug disabled (see backend/Dockerfile).
    create_app().run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "1") == "1")
