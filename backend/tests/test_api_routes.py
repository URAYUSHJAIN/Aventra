"""API tests for market, intelligence and news endpoints. External providers and FinBERT are mocked
or replaced by the local demo dataset, so these tests run offline."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import create_app
from backend.services import intelligence_service
from ml import config
from ml.data import cache
from ml.data.market_providers import ProviderError
from ml.news.finbert import FinBertUnavailable

QUOTE = {"symbol": "RELIANCE", "name": "Reliance Industries", "currency": "INR", "price": 1200.0, "previous_close": 1190.0, "change_pct": 0.84,
         "volume": 1000, "day_high": 1210.0, "day_low": 1180.0, "market_time": "2026-09-25T10:00:00Z", "intraday": [], "interval": "5m"}


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cache.invalidate()
        intelligence_service._cache.clear()
        self.patches = [patch.object(config, "DB_PATH", Path(self.tmp.name) / "api.sqlite3"), patch.object(config, "ARTIFACT_DIR", Path(self.tmp.name) / "artifacts")]
        for p in self.patches:
            p.start()
        self.client = create_app({"TESTING": True}).test_client()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        cache.invalidate()
        intelligence_service._cache.clear()
        self.tmp.cleanup()


class HealthAndValidationTests(ApiTestCase):
    def test_health(self):
        body = self.client.get("/api/health").get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["status"], "ok")
        self.assertIn(body["data"]["data_mode"], {"live", "demo"})

    def test_invalid_symbol_is_400(self):
        response = self.client.get("/api/market/bad!sym")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_unknown_asset_is_404(self):
        self.assertEqual(self.client.get("/api/intelligence/NOTREAL").status_code, 404)

    def test_unknown_route_returns_json_404(self):
        response = self.client.get("/api/does-not-exist")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["success"], False)

    def test_bad_query_parameters(self):
        self.assertEqual(self.client.get("/api/market/quotes").status_code, 400)
        self.assertEqual(self.client.get("/api/market/search?q=a").status_code, 400)
        self.assertEqual(self.client.get("/api/anomalies?limit=abc").status_code, 400)
        self.assertEqual(self.client.post("/api/anomaly/detect", json={"symbol": 5}).status_code, 400)


@patch("ml.data.market_providers.YahooChartProvider.get_quote")
class MarketTests(ApiTestCase):
    def test_quote_success_includes_source(self, get_quote):
        get_quote.return_value = dict(QUOTE)
        data = self.client.get("/api/market/RELIANCE").get_json()["data"]
        self.assertEqual(data["price"], 1200.0)
        self.assertEqual(data["data_source"]["provider"], "yahoo_finance_chart")
        self.assertFalse(data["data_source"]["is_demo"])

    def test_provider_unavailable_is_502_without_internal_details(self, get_quote):
        get_quote.side_effect = ProviderError("socket timeout at 10.0.0.1")
        response = self.client.get("/api/market/RELIANCE")
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("10.0.0.1", response.get_json()["error"])

    def test_provider_not_found_is_404(self, get_quote):
        get_quote.side_effect = ProviderError("No market data found", kind="not_found")
        self.assertEqual(self.client.get("/api/market/NOSUCH").status_code, 404)

    def test_batch_quotes_mark_failures_explicitly(self, get_quote):
        def by_symbol(symbol):   # quotes are fetched concurrently, so answer by symbol rather than call order
            if symbol == "TCS":
                raise ProviderError("down")
            return dict(QUOTE)
        get_quote.side_effect = by_symbol
        quotes = self.client.get("/api/market/quotes?symbols=RELIANCE,TCS").get_json()["data"]["quotes"]
        self.assertEqual([q["status"] for q in quotes], ["ok", "unavailable"])
        self.assertIsNone(quotes[1]["quote"])

    def test_demo_quote_is_labelled_demo(self, _get_quote):
        data = self.client.get("/api/market/DEMO").get_json()["data"]
        self.assertTrue(data["data_source"]["is_demo"])


@patch("ml.correlation.correlate.semantic.similarities", return_value=None)
@patch("ml.news.ingest.get_news_analysis_service", side_effect=FinBertUnavailable("forced"))
class IntelligenceTests(ApiTestCase):
    def test_intelligence_views_and_detail_lookups(self, _finbert, _sim):
        data = self.client.get("/api/intelligence/DEMO").get_json()["data"]
        self.assertEqual(data["symbol"], "DEMO")
        self.assertIn("disclaimer", data)
        event_id = data["events"][0]["event_id"]
        anomaly_id = data["events"][0]["anomaly"]["anomaly_id"]

        fp = self.client.get("/api/fingerprint/DEMO").get_json()["data"]
        self.assertEqual(fp["symbol"], "DEMO")
        self.assertTrue(fp["dimensions"])
        self.assertIn("isolation_forest", self.client.get("/api/anomaly/DEMO").get_json()["data"]["models"])
        self.assertEqual(self.client.get(f"/api/anomalies/{anomaly_id}").get_json()["data"]["anomaly_id"], anomaly_id)
        self.assertEqual(self.client.get(f"/api/events/{event_id}").get_json()["data"]["event_id"], event_id)
        self.assertEqual(self.client.get("/api/events/DEMO").get_json()["data"]["events"][0]["event_id"], event_id)
        risk = self.client.get("/api/risk/DEMO").get_json()["data"]
        self.assertIn(risk["current"]["level"], {"LOW", "MODERATE", "ELEVATED", "HIGH"})
        evidence = self.client.get(f"/api/evidence/{anomaly_id}").get_json()["data"]
        self.assertTrue(evidence["evidence"])
        self.assertEqual(self.client.get("/api/evidence/AN-MISSING").status_code, 404)
        self.assertEqual(self.client.get("/api/events/EV-MISSING").status_code, 404)

    def test_news_endpoint_reports_sentiment_source(self, _finbert, _sim):
        data = self.client.get("/api/news?symbol=DEMO&limit=3").get_json()["data"]
        self.assertEqual(len(data["items"]), 3)
        self.assertEqual(data["data_source"]["sentiment_status"], "cached_demo_outputs")
        self.assertTrue(all(item["is_demo"] for item in data["items"]))


class AnalyzeContractTests(ApiTestCase):
    @patch("backend.routes.news_routes.get_news_analysis_service")
    def test_analyze_keeps_original_fields_and_adds_new_ones(self, get_service):
        get_service.return_value.analyze.return_value = {"label": "negative", "positive_probability": 0.05, "neutral_probability": 0.15, "negative_probability": 0.8, "sentiment_score": -0.75}
        data = self.client.post("/api/news/analyze", json={"text": " Profit fell. "}).get_json()["data"]
        for key in ("label", "positive_probability", "neutral_probability", "negative_probability", "sentiment_score"):
            self.assertIn(key, data)
        self.assertEqual(data["sentiment"], "negative")
        self.assertEqual(data["confidence"], 0.8)
        self.assertEqual(data["source"], "user_input")
        self.assertEqual(data["text"], "Profit fell.")
        self.assertTrue(data["timestamp"].endswith("Z"))

    def test_text_too_long_is_413(self):
        self.assertEqual(self.client.post("/api/news/analyze", json={"text": "x" * 12001}).status_code, 413)


if __name__ == "__main__":
    unittest.main()
