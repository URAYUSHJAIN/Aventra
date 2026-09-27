"""Database-backed job queue.

- enqueue() de-duplicates on `dedupe_key` while an identical job is queued or running.
- claim() is atomic: `SELECT … FOR UPDATE SKIP LOCKED` on PostgreSQL (safe for several workers); a guarded
  single-statement UPDATE on SQLite (one worker).
- fail() retries with exponential backoff until max_attempts; recover_stale() re-queues jobs whose worker died.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, insert, select, update

from ml.data import db, store

STALE_AFTER = timedelta(minutes=20)
BACKOFF_BASE_SECONDS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _row(row) -> dict | None:
    if row is None:
        return None
    out = dict(row)
    for key in ("run_after", "locked_at", "created_at", "updated_at"):
        out[key] = store.iso(out.get(key))
    return out


def enqueue(job_type: str, instrument_id: str | None = None, payload: dict | None = None, *, dedupe_key: str | None = None,
            priority: int = 100, delay_seconds: float = 0, max_attempts: int = 3) -> dict:
    dedupe_key = dedupe_key or f"{job_type}:{instrument_id or ''}"
    with store.begin() as conn:
        existing = conn.execute(select(db.jobs).where(and_(db.jobs.c.dedupe_key == dedupe_key, db.jobs.c.status.in_(["queued", "running"])))
                                .order_by(db.jobs.c.id.desc()).limit(1)).mappings().first()
        if existing:
            return {**_row(existing), "deduplicated": True}
        now = _now()
        result = conn.execute(insert(db.jobs).values(type=job_type, instrument_id=instrument_id, dedupe_key=dedupe_key, status="queued", priority=priority,
                                                     attempts=0, max_attempts=max_attempts, run_after=now + timedelta(seconds=delay_seconds),
                                                     payload=payload or {}, created_at=now, updated_at=now))
        job_id = result.inserted_primary_key[0]
        return {**_row(conn.execute(select(db.jobs).where(db.jobs.c.id == job_id)).mappings().first()), "deduplicated": False}


def claim(worker_id: str, types: set[str] | None = None) -> dict | None:
    now = _now()
    ready = and_(db.jobs.c.status == "queued", db.jobs.c.run_after <= now)
    if types:
        ready = and_(ready, db.jobs.c.type.in_(types))
    with store.begin() as conn:
        if conn.dialect.name == "postgresql":
            candidate = conn.execute(select(db.jobs.c.id).where(ready).order_by(db.jobs.c.priority, db.jobs.c.id).limit(1)
                                     .with_for_update(skip_locked=True)).scalar()
            if candidate is None:
                return None
            conn.execute(update(db.jobs).where(db.jobs.c.id == candidate).values(status="running", locked_by=worker_id, locked_at=now,
                                                                                   attempts=db.jobs.c.attempts + 1, updated_at=now))
        else:
            candidate = conn.execute(select(db.jobs.c.id).where(ready).order_by(db.jobs.c.priority, db.jobs.c.id).limit(1)).scalar()
            if candidate is None:
                return None
            claimed = conn.execute(update(db.jobs).where(and_(db.jobs.c.id == candidate, db.jobs.c.status == "queued"))
                                   .values(status="running", locked_by=worker_id, locked_at=now, attempts=db.jobs.c.attempts + 1, updated_at=now)).rowcount
            if not claimed:
                return None
        return _row(conn.execute(select(db.jobs).where(db.jobs.c.id == candidate)).mappings().first())


def complete(job_id: int, result: dict | None = None) -> None:
    with store.begin() as conn:
        conn.execute(update(db.jobs).where(db.jobs.c.id == job_id).values(status="done", result=result or {}, error=None, updated_at=_now()))


def fail(job_id: int, error: str, retryable: bool = True, detail: dict | None = None) -> str:
    """Record a failure; re-queue with exponential backoff while attempts remain. Returns the new status.

    detail: typed failure state ({"code", "attempts"}) kept in `result` so the API can show which providers were tried."""
    with store.begin() as conn:
        job = conn.execute(select(db.jobs).where(db.jobs.c.id == job_id)).mappings().first()
        if job is None:
            return "missing"
        again = retryable and job["attempts"] < job["max_attempts"]
        status = "queued" if again else "failed"
        delay = timedelta(seconds=BACKOFF_BASE_SECONDS * 2 ** max(job["attempts"] - 1, 0))
        conn.execute(update(db.jobs).where(db.jobs.c.id == job_id).values(status=status, error=error[:1000], result=detail, locked_by=None, locked_at=None,
                                                                           run_after=_now() + delay if again else job["run_after"], updated_at=_now()))
        return status


def recover_stale() -> int:
    cutoff = _now() - STALE_AFTER
    with store.begin() as conn:
        return conn.execute(update(db.jobs).where(and_(db.jobs.c.status == "running", db.jobs.c.locked_at < cutoff))
                            .values(status="queued", locked_by=None, locked_at=None, updated_at=_now())).rowcount


def get(job_id: int) -> dict | None:
    with db.get_engine().connect() as conn:
        return _row(conn.execute(select(db.jobs).where(db.jobs.c.id == job_id)).mappings().first())


def latest_for(dedupe_key: str) -> dict | None:
    with db.get_engine().connect() as conn:
        return _row(conn.execute(select(db.jobs).where(db.jobs.c.dedupe_key == dedupe_key).order_by(db.jobs.c.id.desc()).limit(1)).mappings().first())


def counts() -> dict:
    from sqlalchemy import func
    with db.get_engine().connect() as conn:
        return {status: int(n) for status, n in conn.execute(select(db.jobs.c.status, func.count()).group_by(db.jobs.c.status)).all()}
