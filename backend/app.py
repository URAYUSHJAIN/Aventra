import logging
import os
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from backend.routes.instrument_routes import instrument_api
from backend.routes.intelligence_routes import intelligence_api
from backend.routes.market_routes import market_api
from backend.routes.news_routes import news_api
from backend.services.intelligence_service import AnalysisFailed, AnalysisPending
from backend.utils.responses import ApiError
from ml import config as ml_config
from ml.data import migrate, store
from ml.data.validation import MarketDataError
from ml.instruments import ids
from ml.news.finbert import DEFAULT_MODEL_PATH
from ml.pipelines.intelligence import InsufficientHistory, UnknownAsset
from ml.providers.base import ProviderError
from ml.providers.registry import DataUnavailable

logger = logging.getLogger(__name__)
# Data-availability states → HTTP status. Every one is shown to the user as "Data unavailable / insufficient source data".
UNAVAILABLE = "Data unavailable / insufficient source data"
DATA_STATUS = {"INSTRUMENT_NOT_FOUND": 404, "NO_PROVIDER_FOR_ASSET": 422, "PROVIDER_UNAVAILABLE": 503, "RATE_LIMITED": 503}


def _unavailable_text(error: Exception) -> str:
    text = str(error)
    return text if text.startswith(UNAVAILABLE) else f"{UNAVAILABLE}. {text}"


def create_app(test_config=None):
    app = Flask(__name__)
    configured_origins = os.getenv("CORS_ORIGINS", "*")
    origins = "*" if configured_origins == "*" else [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    app.config.from_mapping(MAX_NEWS_TEXT_LENGTH=12000, CORS_ORIGINS=origins)
    if test_config:
        app.config.update(test_config)

    migrate.upgrade()   # idempotent; keeps SQLite/PostgreSQL at the current schema
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    app.register_blueprint(news_api, url_prefix="/api/news")
    app.register_blueprint(market_api, url_prefix="/api")
    app.register_blueprint(instrument_api, url_prefix="/api")
    app.register_blueprint(intelligence_api, url_prefix="/api")
    _register_error_handlers(app)

    @app.get("/api/health")
    def health():
        model_path = os.getenv("FINBERT_MODEL_PATH", str(DEFAULT_MODEL_PATH))
        try:
            instruments, database = store.count_instruments(), "ok"
        except Exception:
            logger.exception("Database health check failed")
            instruments, database = None, "unavailable"
        return jsonify(success=True, data={
            "status": "ok" if database == "ok" else "degraded",
            "database": database, "database_backend": "postgresql" if os.getenv("AVENTRA_DATABASE_URL", "").startswith("postgresql") else "sqlite",
            "instrument_master_size": instruments,
            "finbert_model_files": "present" if os.path.isfile(os.path.join(model_path, "pytorch_model.bin")) else "missing",
            "synthetic_test_data": ml_config.synthetic_test_data_enabled(),
            "pipeline_version": ml_config.PIPELINE_VERSION,
            "job_mode": os.getenv("AVENTRA_JOB_MODE", "inline"),
        })

    return app


def _register_error_handlers(app: Flask) -> None:
    """Map domain exceptions to the {success: false, error, code} envelope. Messages are safe; stack traces are only logged."""

    @app.errorhandler(ApiError)
    def api_error(error: ApiError):
        return jsonify(success=False, error=error.message, code=error.code), error.status

    @app.errorhandler(AnalysisPending)
    def analysis_pending(pending: AnalysisPending):
        # 202: analysis runs in the background; `previous_result` is an older stored run, clearly labelled as such.
        return jsonify(success=True, data={"status": pending.job["status"], "job": pending.job, "previous_result": pending.previous,
                                           "message": "Analysis queued; poll /api/jobs/<id>."}), 202

    @app.errorhandler(AnalysisFailed)
    def analysis_failed(error: AnalysisFailed):
        status = DATA_STATUS.get(error.code, 422 if error.code.startswith("INSUFFICIENT") else 503)
        return jsonify(success=False, error=_unavailable_text(error), code=error.code, attempts=error.attempts), status

    @app.errorhandler(ids.InvalidInstrumentId)
    def invalid_id(error):
        return jsonify(success=False, error=str(error), code="INVALID_INSTRUMENT_ID"), 400

    @app.errorhandler(UnknownAsset)
    def unknown_asset(error):
        return jsonify(success=False, error=str(error), code="INSTRUMENT_NOT_FOUND"), 404

    @app.errorhandler(InsufficientHistory)
    def insufficient_history(error):
        return jsonify(success=False, error=f"Data unavailable / insufficient source data: {error}", code="INSUFFICIENT_HISTORY"), 422

    @app.errorhandler(DataUnavailable)
    def data_unavailable(error: DataUnavailable):
        attempts = [{k: a.get(k) for k in ("provider", "status", "reason", "detail")} for a in error.attempts]
        return jsonify(success=False, error=_unavailable_text(error), code=error.code, attempts=attempts), DATA_STATUS.get(error.code, 503)

    @app.errorhandler(ProviderError)
    def provider_error(error: ProviderError):
        logger.warning("Provider failure: %s", error)
        return jsonify(success=False, error="The data provider is currently unavailable. Please try again later.", code=getattr(error, "code", "PROVIDER_UNAVAILABLE")), 502

    @app.errorhandler(MarketDataError)
    def market_data_error(error):
        return jsonify(success=False, error="Data unavailable / insufficient source data: the provider's observations failed validation.", code="INSUFFICIENT_SOURCE_DATA"), 422

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        return jsonify(success=False, error=error.description or error.name, code="HTTP_ERROR"), error.code

    @app.errorhandler(Exception)
    def unexpected(error):
        logger.exception("Unhandled API error")
        return jsonify(success=False, error="An unexpected error occurred. Please try again.", code="INTERNAL_ERROR"), 500


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Local development server only; containers use gunicorn with debug disabled (see docker/backend.Dockerfile).
    create_app().run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "1") == "1")
