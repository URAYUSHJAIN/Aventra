"""API tests: instrument search/resolve, snapshots, providers, intelligence and typed data-availability states.
External providers are mocked or replaced by the synthetic TEST:DEMO fixture, so these tests run offline."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from backend.app import create_app
from backend.services import intelligence_service
from ml import config
from ml.data import cache, db, store
from ml.instruments import master
from ml.news.finbert import FinBertUnavailable
from ml.providers import http


def fake_response(status=200, body=None, text=None):
    r = requests.Response()
    r.status_code = status
    r._content = text.encode() if text is not None else json.dumps(body).encode()
    return r


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cache.invalidate()
        http.reset_state()
        intelligence_service._cache.clear()
        self.patches = [patch.dict(os.environ, {"AVENTRA_ENABLE_SYNTHETIC_TEST_DATA": "1", "ALPHAVANTAGE_API_KEY": "", "UPSTOX_ACCESS_TOKEN": "",
                                                "AVENTRA_DEFAULT_WATCHLIST": "FX:USDINR,XNAS:AAPL"}),
                        patch.object(config, "DB_PATH", Path(self.tmp.name) / "api.sqlite3"), patch.object(config, "ARTIFACT_DIR", Path(self.tmp.name) / "artifacts"),
                        patch("time.sleep")]
        for p in self.patches:
            p.start()
        self.client = create_app({"TESTING": True}).test_client()
        from ml.providers.synthetic_test import SyntheticTestProvider
        store.upsert_instruments(*SyntheticTestProvider().list_instruments())
        rows = [master.instrument_row("XNAS:AAPL", "AAPL", "Apple Inc.", "equity", "XNAS", country="US", currency="USD", source="t", class_source="t", class_confidence=1),
                master.instrument_row("FX:USDINR", "USDINR", "US Dollar / Indian Rupee (USD/INR)", "forex", "FX", currency="INR", source="t", class_source="t", class_confidence=1),
                master.instrument_row("XLON:VOD", "VOD", "Vodafone Group", "equity", "XLON", country="GB", currency="GBP", source="t", class_source="t", class_confidence=1)]
        maps = [{"instrument_id": "FX:USDINR", "provider": "frankfurter", "provider_symbol": "USDINR", "priority": 10}]
        store.upsert_instruments(rows, master.alias_rows("XNAS:AAPL", strong=["Apple"], tickers=["AAPL"]), maps)

    def tearDown(self):
        for p in self.patches:
            p.stop()
        cache.invalidate()
        intelligence_service._cache.clear()
        db.dispose_engines()
        self.tmp.cleanup()


class DiscoveryTests(ApiTestCase):
    def test_health_reports_database_and_master(self):
        data = self.client.get("/api/health").get_json()["data"]
        self.assertEqual(data["database"], "ok")
        self.assertEqual(data["instrument_master_size"], 4)

    def test_search_is_ranked_paginated_and_filtered(self):
        data = self.client.get("/api/instruments/search?q=apple").get_json()["data"]
        self.assertEqual(data["items"][0]["instrument_id"], "XNAS:AAPL")
        self.assertEqual(data["items"][0]["asset_class"], "equity")
        page = self.client.get("/api/instruments/search?q=a&limit=1").get_json()["data"]
        self.assertIsNotNone(page["next_cursor"])
        self.assertEqual(self.client.get("/api/instruments/search?q=apple&asset_class=forex").get_json()["data"]["items"], [])
        self.assertEqual(self.client.get("/api/instruments/search?q=a&asset_class=nonsense").status_code, 400)
        self.assertEqual(self.client.get("/api/instruments/search?q=").status_code, 400)

    def test_instrument_detail_lists_provider_configuration(self):
        data = self.client.get("/api/instruments/XNAS:AAPL").get_json()["data"]
        self.assertEqual(data["data_providers"][0]["provider"], "alpha_vantage")
        self.assertFalse(data["data_providers"][0]["configured"])
        self.assertEqual(self.client.get("/api/instruments/XNAS:NOPE").status_code, 404)
        self.assertEqual(self.client.get("/api/instruments/BAD:ID").get_json()["code"], "INVALID_INSTRUMENT_ID")

    def test_resolve_reports_unconfigured_fred(self):
        with patch.dict(os.environ, {"FRED_API_KEY": ""}):
            data = self.client.post("/api/instruments/resolve", json={"query": "treasury"}).get_json()["data"]
        self.assertEqual(data["providers"][0]["status"], "PROVIDER_UNAVAILABLE")
        self.assertEqual(self.client.post("/api/instruments/resolve", json={}).status_code, 400)

    def test_provider_matrix(self):
        providers = {p["provider"]: p for p in self.client.get("/api/providers").get_json()["data"]["providers"]}
        self.assertNotIn("yahoo_finance_chart", providers)
        self.assertFalse(providers["alpha_vantage"]["configured"])
        self.assertEqual(providers["alpha_vantage"]["unavailable_reason"], "missing_credentials")

    def test_default_watchlist_comes_from_configuration(self):
        data = self.client.get("/api/watchlists/default").get_json()["data"]
        self.assertEqual([i["instrument_id"] for i in data["items"]], ["FX:USDINR", "XNAS:AAPL"])


class DataStateTests(ApiTestCase):
    def test_missing_credentials_is_explicit_provider_unavailable(self):
        response = self.client.get("/api/market/XNAS:AAPL")
        self.assertEqual(response.status_code, 503)
        body = response.get_json()
        self.assertEqual(body["code"], "PROVIDER_UNAVAILABLE")
        self.assertIn("Data unavailable / insufficient source data", body["error"])
        self.assertIn("ALPHAVANTAGE_API_KEY", body["attempts"][0]["detail"])

    def test_unsupported_exchange_and_unknown_instrument(self):
        self.assertEqual(self.client.get("/api/market/XLON:VOD").get_json()["code"], "NO_PROVIDER_FOR_ASSET")
        self.assertEqual(self.client.get("/api/intelligence/XNSE:NOTREAL").status_code, 404)
        self.assertEqual(self.client.get("/api/market/bad!id").status_code, 400)

    def test_snapshot_uses_real_provider_series_and_never_invents_volume(self):
        body = {"rates": {f"2026-0{m}-{d:02d}": {"INR": 83 + m / 10 + d / 1000} for m in (6, 7, 8) for d in range(1, 29)}}
        with patch("requests.request", return_value=fake_response(body=body)):
            data = self.client.get("/api/market/FX:USDINR").get_json()["data"]
        self.assertEqual(data["value_kind"], "reference_rate")
        self.assertEqual(data["data_source"]["provider"], "frankfurter")
        self.assertIsNone(data["volume"])
        self.assertEqual(data["instrument"]["currency"], "INR")

    def test_batch_snapshots_carry_per_item_state(self):
        items = self.client.get("/api/market/snapshots?ids=XNAS:AAPL,XLON:VOD,BAD:X").get_json()["data"]["items"]
        self.assertEqual([i["status"] for i in items], ["PROVIDER_UNAVAILABLE", "NO_PROVIDER_FOR_ASSET", "INVALID_INSTRUMENT_ID"])
        self.assertTrue(all(i["snapshot"] is None for i in items))


@patch("ml.correlation.correlate.semantic.similarities", return_value=None)
@patch("ml.news.ingest.get_news_analysis_service", side_effect=FinBertUnavailable("forced"))
class IntelligenceTests(ApiTestCase):
    def test_intelligence_round_trip_on_test_fixture(self, _finbert, _sim):
        data = self.client.get("/api/intelligence/TEST:DEMO").get_json()["data"]
        self.assertEqual(data["instrument_id"], "TEST:DEMO")
        self.assertIn("versions", data)
        event_id, anomaly_id = data["events"][0]["event_id"], data["events"][0]["anomaly"]["anomaly_id"]
        self.assertEqual(self.client.get("/api/fingerprint/TEST:DEMO").get_json()["data"]["instrument_id"], "TEST:DEMO")
        self.assertIn("isolation_forest", self.client.get("/api/anomaly/TEST:DEMO").get_json()["data"]["models"])
        self.assertEqual(self.client.get(f"/api/anomalies/{anomaly_id}").get_json()["data"]["anomaly_id"], anomaly_id)
        self.assertEqual(self.client.get(f"/api/events/{event_id}").get_json()["data"]["event_id"], event_id)
        self.assertEqual(self.client.get("/api/events/TEST:DEMO").get_json()["data"]["events"][0]["event_id"], event_id)
        self.assertIn(self.client.get("/api/risk/TEST:DEMO").get_json()["data"]["current"]["level"], {"LOW", "MODERATE", "ELEVATED", "HIGH"})
        evidence = self.client.get(f"/api/evidence/{anomaly_id}").get_json()["data"]["evidence"]
        self.assertTrue(evidence and all("provenance" in item for item in evidence))
        self.assertEqual(self.client.post("/api/anomaly/detect", json={"instrument_id": "TEST:DEMO"}).status_code, 200)
        self.assertEqual(self.client.get("/api/evidence/AN-MISSING").status_code, 404)

    def test_news_endpoint_for_instrument(self, _finbert, _sim):
        data = self.client.get("/api/news?instrument=TEST:DEMO&limit=3").get_json()["data"]
        self.assertEqual(len(data["items"]), 3)
        self.assertEqual(data["data_source"]["sentiment_status"], "cached_demo_outputs")


class AnalyzeContractTests(ApiTestCase):
    @patch("backend.routes.news_routes.get_news_analysis_service")
    def test_analyze_keeps_original_fields_and_adds_new_ones(self, get_service):
        get_service.return_value.analyze.return_value = {"label": "negative", "positive_probability": 0.05, "neutral_probability": 0.15, "negative_probability": 0.8, "sentiment_score": -0.75}
        data = self.client.post("/api/news/analyze", json={"text": " Profit fell. "}).get_json()["data"]
        for key in ("label", "positive_probability", "neutral_probability", "negative_probability", "sentiment_score"):
            self.assertIn(key, data)
        self.assertEqual((data["sentiment"], data["confidence"], data["source"], data["text"]), ("negative", 0.8, "user_input", "Profit fell."))

    def test_text_too_long_is_413(self):
        self.assertEqual(self.client.post("/api/news/analyze", json={"text": "x" * 12001}).status_code, 413)


if __name__ == "__main__":
    unittest.main()
