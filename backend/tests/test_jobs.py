"""Phase 9: job queue semantics and the asynchronous analysis API (external worker mode, processed explicitly)."""
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import update

from backend.app import create_app
from ml import config
from ml.data import cache, db, store
from ml.jobs import queue
from ml.jobs.worker import Worker, run_job
from ml.news.finbert import FinBertUnavailable
from ml.providers import http


class JobTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cache.invalidate()
        http.reset_state()
        self.patches = [patch.dict(os.environ, {"AVENTRA_ENABLE_SYNTHETIC_TEST_DATA": "1", "AVENTRA_JOB_MODE": "external", "ALPHAVANTAGE_API_KEY": ""}),
                        patch.object(config, "DB_PATH", Path(self.tmp.name) / "jobs.sqlite3"), patch.object(config, "ARTIFACT_DIR", Path(self.tmp.name) / "a"),
                        patch("ml.news.ingest.get_news_analysis_service", side_effect=FinBertUnavailable("forced")),
                        patch("ml.correlation.correlate.semantic.similarities", return_value=None), patch("time.sleep")]
        for p in self.patches:
            p.start()
        self.client = create_app({"TESTING": True}).test_client()
        from ml.instruments import master
        from ml.providers.synthetic_test import SyntheticTestProvider
        store.upsert_instruments(*SyntheticTestProvider().list_instruments())
        store.upsert_instruments([master.instrument_row("XNAS:AAPL", "AAPL", "Apple Inc.", "equity", "XNAS", country="US", currency="USD", source="t",
                                                        class_source="t", class_confidence=1)])

    def tearDown(self):
        for p in self.patches:
            p.stop()
        cache.invalidate()
        db.dispose_engines()
        self.tmp.cleanup()


class QueueTests(JobTestCase):
    def test_enqueue_deduplicates_and_claim_is_exclusive(self):
        first = queue.enqueue("analyze", "TEST:DEMO")
        second = queue.enqueue("analyze", "TEST:DEMO")
        self.assertFalse(first["deduplicated"])
        self.assertTrue(second["deduplicated"])
        self.assertEqual(first["id"], second["id"])
        claimed = queue.claim("w1")
        self.assertEqual((claimed["id"], claimed["status"], claimed["attempts"]), (first["id"], "running", 1))
        self.assertIsNone(queue.claim("w2"))

    def test_failure_retries_with_backoff_then_fails(self):
        job = queue.enqueue("analyze", "XNAS:AAPL", max_attempts=2)
        queue.claim("w")
        self.assertEqual(queue.fail(job["id"], "RATE_LIMITED: slow down"), "queued")
        self.assertGreater(store.utc(queue.get(job["id"])["run_after"]), datetime.now(timezone.utc))   # backoff delay
        self.assertIsNone(queue.claim("w"))                                                         # not ready yet
        with store.begin() as conn:
            conn.execute(update(db.jobs).values(run_after=datetime.now(timezone.utc) - timedelta(seconds=1)))
        queue.claim("w")
        self.assertEqual(queue.fail(job["id"], "RATE_LIMITED: again"), "failed")

    def test_stale_running_jobs_are_recovered(self):
        job = queue.enqueue("analyze", "TEST:DEMO")
        queue.claim("dead-worker")
        with store.begin() as conn:
            conn.execute(update(db.jobs).values(locked_at=datetime.now(timezone.utc) - timedelta(hours=1)))
        self.assertEqual(queue.recover_stale(), 1)
        self.assertEqual(queue.get(job["id"])["status"], "queued")

    def test_missing_credentials_is_not_retried(self):
        job = queue.enqueue("analyze", "XNAS:AAPL")
        self.assertEqual(run_job(queue.claim("w")), "failed")
        self.assertIn("PROVIDER_UNAVAILABLE", queue.get(job["id"])["error"])

    def test_unexpected_errors_are_not_typed_and_hide_internals(self):
        class LibraryError(Exception):
            code = "f405"                     # SQLAlchemy-style error code: not an Aventra data state
        job = queue.enqueue("sync_listings", max_attempts=1)
        with patch.dict("ml.jobs.worker.HANDLERS", {"sync_listings": lambda _job: (_ for _ in ()).throw(LibraryError("INSERT INTO instruments ... secret SQL"))}),                 self.assertLogs("ml.jobs.worker", level="ERROR"):
            self.assertEqual(run_job(queue.claim("w")), "failed")
        record = queue.get(job["id"])
        self.assertTrue(record["error"].startswith("INTERNAL_ERROR"))
        self.assertNotIn("SQL", record["error"])


class AsyncApiTests(JobTestCase):
    def test_intelligence_is_queued_then_served(self):
        response = self.client.get("/api/intelligence/TEST:DEMO")
        self.assertEqual(response.status_code, 202)
        job = response.get_json()["data"]["job"]
        self.assertEqual(self.client.get(f"/api/jobs/{job['id']}").get_json()["data"]["status"], "queued")
        self.assertEqual(Worker("test").process_ready(), 1)
        self.assertEqual(self.client.get(f"/api/jobs/{job['id']}").get_json()["data"]["status"], "done")
        result = self.client.get("/api/intelligence/TEST:DEMO")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.get_json()["data"]["instrument_id"], "TEST:DEMO")
        self.assertEqual(self.client.post("/api/intelligence/TEST:DEMO/runs").status_code, 202)

    def test_failed_job_returns_typed_state(self):
        self.assertEqual(self.client.get("/api/intelligence/XNAS:AAPL").status_code, 202)
        Worker("test").process_ready()
        response = self.client.get("/api/intelligence/XNAS:AAPL")
        self.assertEqual(response.status_code, 503)
        body = response.get_json()
        self.assertEqual(body["code"], "PROVIDER_UNAVAILABLE")
        self.assertEqual(body["error"].count("Data unavailable / insufficient source data"), 1)
        self.assertTrue(body["attempts"])                                             # which providers were tried, and why they failed
        self.assertTrue(all(a["reason"] == "missing_credentials" for a in body["attempts"]))
        self.assertEqual(self.client.get("/api/jobs/999999").status_code, 404)
        self.assertEqual(self.client.get("/api/intelligence/XNSE:NOPE").status_code, 404)   # unknown instruments are never queued


if __name__ == "__main__":
    unittest.main()
