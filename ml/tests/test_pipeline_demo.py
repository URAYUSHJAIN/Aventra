"""Integration: the whole pipeline on the synthetic TEST:DEMO instrument, fully offline.

The synthetic provider exists only when AVENTRA_ENABLE_SYNTHETIC_TEST_DATA=1 (set here). FinBERT is forced
unavailable so the cached-test-sentiment path runs without model weights; the semantic model is disabled for speed.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ml import config
from ml.data import cache, db, migrate, store
from ml.news.finbert import FinBertUnavailable


class DemoPipelineTests(unittest.TestCase):
    def setUp(self):
        if not (config.DEMO_DIR / "market.csv").is_file():
            self.skipTest("Test fixture missing; run py -3.12 -m scripts.generate_demo_data")
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        cache.invalidate()
        self.patches = [
            patch.dict(os.environ, {"AVENTRA_ENABLE_SYNTHETIC_TEST_DATA": "1"}),
            patch.object(config, "DB_PATH", tmp / "test.sqlite3"),
            patch.object(config, "ARTIFACT_DIR", tmp / "artifacts"),
            patch("ml.news.ingest.get_news_analysis_service", side_effect=FinBertUnavailable("forced")),
            patch("ml.correlation.correlate.semantic.similarities", return_value=None),
        ]
        for p in self.patches:
            p.start()
        migrate.upgrade()
        from ml.providers.synthetic_test import SyntheticTestProvider
        store.upsert_instruments(*SyntheticTestProvider().list_instruments())

    def tearDown(self):
        for p in self.patches:
            p.stop()
        cache.invalidate()
        db.dispose_engines()
        self.tmp.cleanup()

    def test_demo_scenario_end_to_end(self):
        from ml.pipelines.intelligence import run_intelligence
        result = run_intelligence("TEST:DEMO")
        self.assertEqual(result["instrument_id"], "TEST:DEMO")
        self.assertTrue(result["data_source"]["market"]["is_demo"])
        self.assertEqual(result["feature_set"], "ohlcv")
        self.assertTrue(result["versions"]["feature_set"].startswith("ohlcv-v1-"))
        dates = [event["trading_date"] for event in result["events"]]
        self.assertIn("2026-06-15", dates)     # the injected scenario session
        event = next(e for e in result["events"] if e["trading_date"] == "2026-06-15")
        self.assertIn(event["anomaly"]["severity"], {"HIGH", "CRITICAL"})
        self.assertEqual(event["correlation"]["status"], "aligned_news_found")
        self.assertEqual(event["correlation"]["matches"][0]["sentiment"]["label"], "negative")
        self.assertEqual(event["risk"]["basis"], "market_and_news")
        types = {item["type"] for item in event["evidence"]}
        self.assertTrue({"volume", "price", "news", "sentiment", "correlation", "anomaly", "risk"} <= types)
        self.assertTrue(all("provenance" in item for item in event["evidence"]))
        self.assertEqual(next(i for i in event["evidence"] if i["type"] == "volume")["provenance"]["provider"], "aventra_demo_dataset")
        self.assertNotIn("caused", " ".join(item["description"] for item in event["evidence"]).lower())
        self.assertEqual(result["data_source"]["news"]["sentiment_status"], "cached_demo_outputs")
        self.assertEqual(store.latest_run("TEST:DEMO")["run_id"], result["run_id"])
        self.assertEqual(store.get_event_by("anomaly_id", event["anomaly"]["anomaly_id"])["event_id"], event["event_id"])

    def test_unknown_instrument(self):
        from ml.pipelines.intelligence import UnknownAsset, run_intelligence
        with self.assertRaises(UnknownAsset):
            run_intelligence("XNSE:NOTREAL")

    def test_synthetic_provider_is_absent_without_test_flag(self):
        from ml.providers import registry
        with patch.dict(os.environ, {"AVENTRA_ENABLE_SYNTHETIC_TEST_DATA": ""}):
            with self.assertRaises(registry.DataUnavailable):
                registry.fetch_history(store.get_instrument("TEST:DEMO"))


if __name__ == "__main__":
    unittest.main()
