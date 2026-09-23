import logging
import os
from flask import Flask, jsonify
from flask_cors import CORS

from backend.routes.news_routes import news_api


def create_app(test_config=None):
    app = Flask(__name__)
    configured_origins = os.getenv("CORS_ORIGINS", "*")
    origins = "*" if configured_origins == "*" else [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    app.config.from_mapping(MAX_NEWS_TEXT_LENGTH=12000, CORS_ORIGINS=origins)
    if test_config:
        app.config.update(test_config)

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    app.register_blueprint(news_api, url_prefix="/api/news")

    @app.get("/api/health")
    def health():
        return jsonify(success=True, data={"status": "ok"})

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    create_app().run(host="0.0.0.0", port=5000, debug=True)
