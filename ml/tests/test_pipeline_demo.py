"""Integration: the whole pipeline on the synthetic demo dataset, fully offline.

FinBERT is forced unavailable so the test exercises the cached-demo-sentiment path
and runs without model weights; the semantic model is disabled for speed.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ml import config
from ml.data import cache, store
from ml.news.finbert import FinBertUnavailable


class DemoPipelineTests(unittest.TestCase):
    def setUp(self):
        if not (config.DEMO_DIR / "market.csv").is_file():
            self.skipTest("Demo dataset missing; run py -3.12 -m scripts.generate_demo_data")
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        cache.invalidate()
        self.patches = [
            patch.object(config, "DB_PATH", tmp / "test.sqlite3"),
            patch.object(config, "ARTIFACT_DIR", tmp / "artifacts"),
            patch("ml.news.ingest.get_news_analysis_service", side_effect=FinBertUnavailable("forced")),
            patch("ml.correlation.correlate.semantic.similarities", return_value=None),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        cache.invalidate()
        self.tmp.cleanup()

    def test_demo_scenario_end_to_end(self):
        from ml.pipelines.intelligence import run_intelligence
        result = run_intelligence("DEMO")
        self.assertTrue(result["data_source"]["market"]["is_demo"])
        dates = [event["trading_date"] for event in result["events"]]
        self.assertIn("2026-06-15", dates)     # the injected scenario session
        event = next(e for e in result["events"] if e["trading_date"] == "2026-06-15")
        self.assertIn(event["anomaly"]["severity"], {"HIGH", "CRITICAL"})
        self.assertEqual(event["correlation"]["status"], "aligned_news_found")
        self.assertEqual(event["correlation"]["matches"][0]["sentiment"]["label"], "negative")
        self.assertEqual(event["risk"]["basis"], "market_and_news")
        types = {item["type"] for item in event["evidence"]}
        self.assertTrue({"volume", "price", "news", "sentiment", "correlation", "anomaly", "risk"} <= types)
        self.assertNotIn("caused", " ".join(item["description"] for item in event["evidence"]).lower())
        self.assertEqual(result["data_source"]["news"]["sentiment_status"], "cached_demo_outputs")

        # persisted and retrievable
        self.assertEqual(store.latest_run("DEMO")["run_id"], result["run_id"])
        self.assertEqual(store.get_event_by("anomaly_id", event["anomaly"]["anomaly_id"])["event_id"], event["event_id"])

    def test_unknown_asset(self):
        from ml.pipelines.intelligence import UnknownAsset, run_intelligence
        with self.assertRaises(UnknownAsset):
            run_intelligence("NOTREAL")


if __name__ == "__main__":
    unittest.main()
