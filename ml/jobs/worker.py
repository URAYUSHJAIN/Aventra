"""Job handlers, scheduler and worker process.

    py -3.12 -m ml.jobs.worker            # long-running worker (Docker `worker` service)
    py -3.12 -m ml.jobs.worker --once     # process everything that is ready, then exit

Handlers: analyze, refresh_prices, refresh_news, sync_listings, enrich_crypto, refine_classes.
Scheduler (worker only): listing sync every 24 h; tracked instruments (default watchlist + instruments analysed in the
last 7 days) re-analysed once per day. Provider limits are enforced by ml/providers/http.py for every call, and a
job that hits PROVIDER_UNAVAILABLE / RATE_LIMITED is retried with backoff rather than hammering the provider.
FinBERT and the semantic model load once per worker process (module-level singletons).
"""
from __future__ import annotations

import logging
import os
import signal
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select

from ml import config
from ml.data import db, store
from ml.jobs import queue

logger = logging.getLogger(__name__)
POLL_SECONDS = float(os.getenv("AVENTRA_WORKER_POLL_SECONDS", "3"))
SCHEDULE_EVERY = timedelta(minutes=10)
LISTING_MAX_AGE = timedelta(hours=24)
TRACK_WINDOW = timedelta(days=7)


# ------------------------------------------------------------------------------------------------ handlers
def _analyze(job: dict) -> dict:
    from ml.pipelines.intelligence import run_intelligence
    result = run_intelligence(job["instrument_id"], persist=True, force_refresh=bool((job.get("payload") or {}).get("refresh")))
    return {"run_id": result["run_id"], "flagged": result["anomaly"]["flagged_count"], "risk": result["current_assessment"]["risk"]["score"]}


def _refresh_prices(job: dict) -> dict:
    from ml.data.market_data import load_series
    from ml.pipelines.intelligence import resolve_instrument
    bars, source, _ = load_series(resolve_instrument(job["instrument_id"]), force_refresh=True)
    return {"rows": int(len(bars)), "provider": source["provider"], "stale": source["stale"]}


def _refresh_news(job: dict) -> dict:
    from ml.news.ingest import ingest_news
    from ml.pipelines.intelligence import resolve_instrument
    report = ingest_news(job["instrument_id"], resolve_instrument(job["instrument_id"]))
    return {"status": report["status"], "items": len(report["items"])}


def _sync_listings(job: dict) -> dict:
    from ml.instruments.sync import sync_all
    return {"results": sync_all((job.get("payload") or {}).get("providers"))}


def _enrich_crypto(job: dict) -> dict:
    from ml.instruments.sync import enrich_crypto
    return enrich_crypto()


def _refine_classes(job: dict) -> dict:
    from ml.instruments.sync import refine_with_openfigi
    return refine_with_openfigi(int((job.get("payload") or {}).get("limit", 250)))


HANDLERS = {"analyze": _analyze, "refresh_prices": _refresh_prices, "refresh_news": _refresh_news, "sync_listings": _sync_listings,
            "enrich_crypto": _enrich_crypto, "refine_classes": _refine_classes}
NON_RETRYABLE = {"INSTRUMENT_NOT_FOUND", "NO_PROVIDER_FOR_ASSET", "INSUFFICIENT_HISTORY", "INVALID_INSTRUMENT_ID", "INSUFFICIENT_SOURCE_DATA"}


def run_job(job: dict) -> str:
    handler = HANDLERS.get(job["type"])
    if handler is None:
        queue.fail(job["id"], f"unknown job type {job['type']}", retryable=False)
        return "failed"
    try:
        result = handler(job)
    except Exception as error:   # every failure is recorded on the job; typed provider states decide retry
        code = getattr(error, "code", type(error).__name__)
        if not getattr(error, "code", None):
            logger.exception("Job %s (%s) failed", job["id"], job["type"])
        attempts = getattr(error, "attempts", None) or []
        # Retrying cannot help when every provider lacks credentials (configuration, not a transient failure).
        missing_credentials = bool(attempts) and all(a.get("reason") == "missing_credentials" for a in attempts)
        status = queue.fail(job["id"], f"{code}: {error}", retryable=code not in NON_RETRYABLE and not missing_credentials)
        logger.info("job=%s type=%s instrument=%s status=%s code=%s", job["id"], job["type"], job.get("instrument_id"), status, code)
        return status
    queue.complete(job["id"], result)
    logger.info("job=%s type=%s instrument=%s status=done", job["id"], job["type"], job.get("instrument_id"))
    return "done"


# ------------------------------------------------------------------------------------------------ scheduler
def tracked_instruments() -> list[str]:
    from ml.instruments.master import ensure_default_watchlist
    since = datetime.now(timezone.utc) - TRACK_WINDOW
    with db.get_engine().connect() as conn:
        recent = conn.execute(select(db.analysis_runs.c.instrument_id).where(db.analysis_runs.c.created_at >= since).distinct()).scalars().all()
    return list(dict.fromkeys(ensure_default_watchlist() + [iid for iid in recent if not iid.startswith("TEST:")]))


def schedule() -> dict:
    enqueued = {"sync_listings": 0, "analyze": 0}
    last = store.last_listing_snapshot("binance")
    if last is None or datetime.now(timezone.utc) - store.utc(last["fetched_at"]) > LISTING_MAX_AGE:
        if not queue.enqueue("sync_listings", dedupe_key="sync_listings", priority=50)["deduplicated"]:
            enqueued["sync_listings"] += 1
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    for iid in tracked_instruments():
        done_today = queue.latest_for(f"analyze:{iid}:{day}")
        if done_today is None:
            queue.enqueue("analyze", iid, {"scheduled": True}, dedupe_key=f"analyze:{iid}:{day}", priority=150)
            enqueued["analyze"] += 1
    return enqueued


# ------------------------------------------------------------------------------------------------ worker
class Worker:
    def __init__(self, worker_id: str | None = None):
        self.worker_id = worker_id or f"{socket.gethostname()}-{os.getpid()}"
        self.stopping = threading.Event()

    def process_ready(self, max_jobs: int | None = None) -> int:
        processed = 0
        while not self.stopping.is_set() and (max_jobs is None or processed < max_jobs):
            job = queue.claim(self.worker_id)
            if job is None:
                break
            run_job(job)
            processed += 1
        return processed

    def run_forever(self) -> None:
        last_schedule = datetime.min.replace(tzinfo=timezone.utc)
        logger.info("worker %s started", self.worker_id)
        while not self.stopping.is_set():
            queue.recover_stale()
            if datetime.now(timezone.utc) - last_schedule >= SCHEDULE_EVERY:
                logger.info("scheduler enqueued %s", schedule())
                last_schedule = datetime.now(timezone.utc)
            if not self.process_ready(max_jobs=10):
                self.stopping.wait(POLL_SECONDS)
        logger.info("worker %s stopped", self.worker_id)


# In-process dispatcher for single-process deployments (AVENTRA_JOB_MODE=inline, the default outside Docker):
# jobs still go through the queue, but a small thread pool in the API process executes them.
_inline_pool = ThreadPoolExecutor(max_workers=int(os.getenv("AVENTRA_INLINE_JOB_THREADS", "2")), thread_name_prefix="aventra-job")
_inline_worker = Worker(worker_id=f"inline-{os.getpid()}")


def dispatch() -> None:
    if os.getenv("AVENTRA_JOB_MODE", "inline").strip().lower() == "inline":
        _inline_pool.submit(_inline_worker.process_ready, 5)


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from ml.data import migrate
    migrate.upgrade()
    worker = Worker()
    if "--once" in argv:
        print({"processed": worker.process_ready()})
        return 0
    signal.signal(signal.SIGTERM, lambda *_: worker.stopping.set())
    signal.signal(signal.SIGINT, lambda *_: worker.stopping.set())
    worker.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
