"""SQLite persistence (Final Plan §18). Parameterised SQL only; schema kept portable to PostgreSQL.

Tables: prices, news, news_links, news_sentiment, pipeline_runs (model metadata +
full result), anomalies, events, risk_assessments, evidence.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

import pandas as pd

from ml import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    symbol TEXT NOT NULL, timestamp TEXT NOT NULL, open REAL, high REAL, low REAL, close REAL, adj_close REAL,
    volume REAL, source TEXT NOT NULL, fetched_at TEXT NOT NULL, PRIMARY KEY (symbol, timestamp));
CREATE TABLE IF NOT EXISTS news (
    news_id TEXT PRIMARY KEY, headline TEXT NOT NULL, summary TEXT, source TEXT, url TEXT, published_at TEXT NOT NULL,
    provider TEXT NOT NULL, is_demo INTEGER NOT NULL DEFAULT 0, fetched_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS news_links (
    news_id TEXT NOT NULL, symbol TEXT NOT NULL, entity_match_confidence REAL NOT NULL, mapping_method TEXT NOT NULL,
    PRIMARY KEY (news_id, symbol));
CREATE TABLE IF NOT EXISTS news_sentiment (
    news_id TEXT PRIMARY KEY, label TEXT NOT NULL, positive_probability REAL, neutral_probability REAL, negative_probability REAL,
    sentiment_score REAL, confidence REAL, model TEXT NOT NULL, model_version TEXT, analysed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, created_at TEXT NOT NULL, pipeline_version TEXT NOT NULL,
    data_source_json TEXT, models_json TEXT, params_json TEXT, result_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS anomalies (
    anomaly_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, symbol TEXT NOT NULL, timestamp TEXT NOT NULL,
    statistical_score REAL, fingerprint_score REAL, ml_score REAL, anomaly_score REAL, severity TEXT, detail_json TEXT);
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY, anomaly_id TEXT NOT NULL, symbol TEXT NOT NULL, start_time TEXT, end_time TEXT,
    correlation_score REAL, detail_json TEXT);
CREATE TABLE IF NOT EXISTS risk_assessments (
    assessment_id TEXT PRIMARY KEY, anomaly_id TEXT NOT NULL, symbol TEXT NOT NULL, risk_score REAL, risk_level TEXT,
    components_json TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence (
    anomaly_id TEXT NOT NULL, seq INTEGER NOT NULL, timestamp TEXT, type TEXT, description TEXT, value REAL, source TEXT,
    linked_url TEXT, PRIMARY KEY (anomaly_id, seq));
CREATE INDEX IF NOT EXISTS idx_news_published ON news (published_at);
CREATE INDEX IF NOT EXISTS idx_links_symbol ON news_links (symbol);
CREATE INDEX IF NOT EXISTS idx_runs_symbol ON pipeline_runs (symbol, created_at);
CREATE INDEX IF NOT EXISTS idx_anomalies_symbol ON anomalies (symbol, timestamp);
"""

_init_lock = Lock()
_initialised: set[str] = set()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def connect(db_path: Path | None = None):
    path = Path(db_path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        with _init_lock:
            if str(path) not in _initialised:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.executescript(SCHEMA)
                _initialised.add(str(path))
        yield connection
        connection.commit()
    finally:
        connection.close()


# --- prices ------------------------------------------------------------------------------
def upsert_prices(frame: pd.DataFrame, db_path: Path | None = None) -> int:
    fetched = now_iso()
    rows = [
        (row.symbol, row.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"), _num(row.open), _num(row.high), _num(row.low), _num(row.close),
         _num(getattr(row, "adj_close", None)), _num(row.volume), row.source, fetched)
        for row in frame.itertuples(index=False)
    ]
    with connect(db_path) as db:
        db.executemany("INSERT OR REPLACE INTO prices VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def load_prices(symbol: str, db_path: Path | None = None) -> tuple[pd.DataFrame, str | None]:
    with connect(db_path) as db:
        rows = db.execute("SELECT * FROM prices WHERE symbol = ? ORDER BY timestamp", (symbol,)).fetchall()
    if not rows:
        return pd.DataFrame(), None
    frame = pd.DataFrame([dict(row) for row in rows])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return frame, max(frame["fetched_at"])


# --- news ----------------------------------------------------------------------------------
def upsert_news(items: list[dict], db_path: Path | None = None) -> None:
    fetched = now_iso()
    with connect(db_path) as db:
        for item in items:
            db.execute(
                "INSERT OR IGNORE INTO news VALUES (?,?,?,?,?,?,?,?,?)",
                (item["news_id"], item["headline"], item.get("summary"), item.get("source"), item.get("url"), item["published_at"], item["provider"], int(item.get("is_demo", False)), fetched),
            )
            for link in item.get("links", []):
                db.execute("INSERT OR REPLACE INTO news_links VALUES (?,?,?,?)", (item["news_id"], link["symbol"], link["entity_match_confidence"], link["mapping_method"]))


def load_news(symbol: str | None = None, limit: int = 50, db_path: Path | None = None) -> list[dict]:
    query = (
        "SELECT n.*, l.symbol, l.entity_match_confidence, l.mapping_method, s.label, s.positive_probability, s.neutral_probability, "
        "s.negative_probability, s.sentiment_score, s.confidence, s.model, s.model_version "
        "FROM news n JOIN news_links l ON l.news_id = n.news_id LEFT JOIN news_sentiment s ON s.news_id = n.news_id "
    )
    params: tuple = ()
    if symbol:
        query += "WHERE l.symbol = ? "
        params = (symbol,)
    query += "ORDER BY n.published_at DESC LIMIT ?"
    with connect(db_path) as db:
        return [dict(row) for row in db.execute(query, params + (limit,)).fetchall()]


def sentiment_for(news_ids: list[str], db_path: Path | None = None) -> dict[str, dict]:
    if not news_ids:
        return {}
    placeholders = ",".join("?" for _ in news_ids)
    with connect(db_path) as db:
        rows = db.execute(f"SELECT * FROM news_sentiment WHERE news_id IN ({placeholders})", tuple(news_ids)).fetchall()
    return {row["news_id"]: dict(row) for row in rows}


def upsert_sentiment(results: dict[str, dict], db_path: Path | None = None) -> None:
    analysed = now_iso()
    with connect(db_path) as db:
        db.executemany(
            "INSERT OR REPLACE INTO news_sentiment VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(news_id, r["label"], r["positive_probability"], r["neutral_probability"], r["negative_probability"], r["sentiment_score"], r["confidence"], r["model"], r.get("model_version"), analysed) for news_id, r in results.items()],
        )


# --- pipeline results ---------------------------------------------------------------------------
def save_run(result: dict, db_path: Path | None = None) -> None:
    symbol, run_id = result["symbol"], result["run_id"]
    with connect(db_path) as db:
        db.execute(
            "INSERT OR REPLACE INTO pipeline_runs VALUES (?,?,?,?,?,?,?,?)",
            (run_id, symbol, result["generated_at"], result["pipeline_version"], json.dumps(result.get("data_source")), json.dumps(result.get("models")), json.dumps(result.get("parameters")), json.dumps(result)),
        )
        for event in result.get("events", []):
            anomaly = event["anomaly"]
            db.execute(
                "INSERT OR REPLACE INTO anomalies VALUES (?,?,?,?,?,?,?,?,?,?)",
                (anomaly["anomaly_id"], run_id, symbol, anomaly["timestamp"], anomaly["scores"]["statistical"], anomaly["scores"]["fingerprint"], anomaly["scores"]["isolation_forest"], anomaly["anomaly_score"], anomaly["severity"], json.dumps(anomaly)),
            )
            db.execute(
                "INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?)",
                (event["event_id"], anomaly["anomaly_id"], symbol, event["window"]["start"], event["window"]["end"], event["correlation"]["best_score"], json.dumps(event)),
            )
            risk = event["risk"]
            db.execute(
                "INSERT OR REPLACE INTO risk_assessments VALUES (?,?,?,?,?,?,?)",
                (f"RA-{anomaly['anomaly_id']}", anomaly["anomaly_id"], symbol, risk["score"], risk["level"], json.dumps(risk["components"]), result["generated_at"]),
            )
            db.execute("DELETE FROM evidence WHERE anomaly_id = ?", (anomaly["anomaly_id"],))
            db.executemany(
                "INSERT INTO evidence VALUES (?,?,?,?,?,?,?,?)",
                [(anomaly["anomaly_id"], seq, item.get("timestamp"), item["type"], item["description"], _num(item.get("value")), item["source"], item.get("url")) for seq, item in enumerate(event["evidence"])],
            )


def latest_run(symbol: str, db_path: Path | None = None) -> dict | None:
    with connect(db_path) as db:
        row = db.execute("SELECT result_json FROM pipeline_runs WHERE symbol = ? ORDER BY created_at DESC LIMIT 1", (symbol,)).fetchone()
    return json.loads(row["result_json"]) if row else None


def get_event_by(column: str, value: str, db_path: Path | None = None) -> dict | None:
    if column not in {"event_id", "anomaly_id"}:
        raise ValueError("Unsupported lookup column")
    with connect(db_path) as db:
        row = db.execute(f"SELECT detail_json FROM events WHERE {column} = ?", (value,)).fetchone()
    return json.loads(row["detail_json"]) if row else None


def list_anomalies(symbol: str | None = None, limit: int = 100, db_path: Path | None = None) -> list[dict]:
    query, params = "SELECT detail_json FROM anomalies ", ()
    if symbol:
        query, params = query + "WHERE symbol = ? ", (symbol,)
    with connect(db_path) as db:
        rows = db.execute(query + "ORDER BY timestamp DESC LIMIT ?", params + (limit,)).fetchall()
    return [json.loads(row["detail_json"]) for row in rows]


def list_events(symbol: str | None = None, limit: int = 100, db_path: Path | None = None) -> list[dict]:
    query, params = "SELECT detail_json FROM events ", ()
    if symbol:
        query, params = query + "WHERE symbol = ? ", (symbol,)
    with connect(db_path) as db:
        rows = db.execute(query + "ORDER BY start_time DESC LIMIT ?", params + (limit,)).fetchall()
    return [json.loads(row["detail_json"]) for row in rows]


def _num(value):
    if value is None:
        return None
    try:
        return None if pd.isna(value) else float(value)
    except (TypeError, ValueError):
        return None
