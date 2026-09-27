"""Database schema and engine (SQLAlchemy Core). PostgreSQL in Docker/production; SQLite for tests and light local runs.

`instrument_id` (canonical ID such as `XNSE:RELIANCE`, see ml/instruments/ids.py) is the relationship key
everywhere. Schema changes are made only through Alembic migrations (backend/migrations/).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from sqlalchemy import (JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, MetaData, String, Table, Text,
                        UniqueConstraint, create_engine, event)
from sqlalchemy.engine import Engine

from ml import config

metadata = MetaData()
ID = String(80)          # canonical instrument ID
TS = DateTime(timezone=True)

instruments = Table(
    "instruments", metadata,
    Column("instrument_id", ID, primary_key=True),
    Column("symbol", String(64), nullable=False),
    Column("name", Text, nullable=False),
    Column("asset_class", String(24), nullable=False),        # equity, etf, reit, index, mutual_fund, forex, crypto, rate, commodity
    Column("exchange", String(24)),                            # MIC or venue code (XNSE, XBOM, XNAS, BINANCE, FX, AMFI, FRED)
    Column("country", String(2)),
    Column("currency", String(12)),
    Column("timezone", String(48)),
    Column("calendar_code", String(24)),                       # exchange_calendars code or 24/7, 24/5
    Column("isin", String(12)),
    Column("status", String(16), nullable=False, default="listed"),   # listed, resolved, unavailable, delisted, inactive
    Column("class_source", String(48)),                        # which source/rule decided asset_class
    Column("class_confidence", Float),
    Column("capabilities", JSON),                              # has_ohlc, has_volume, value_kind, ...
    Column("benchmark_id", ID),
    Column("source", String(48), nullable=False),              # listing that created the row
    Column("search_text", Text),                               # normalised symbol + name (+ compact form) for token search
    Column("popularity", Float),                               # lower = more prominent (e.g. CoinGecko market-cap rank); NULL = unknown
    Column("created_at", TS, nullable=False),
    Column("updated_at", TS, nullable=False),
)
Index("ix_instruments_symbol", instruments.c.symbol)
Index("ix_instruments_class", instruments.c.asset_class, instruments.c.exchange)
Index("ix_instruments_isin", instruments.c.isin)

instrument_aliases = Table(
    "instrument_aliases", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("instrument_id", ID, ForeignKey("instruments.instrument_id", ondelete="CASCADE"), nullable=False),
    Column("alias", Text, nullable=False),
    Column("alias_norm", String(200), nullable=False),
    Column("kind", String(12), nullable=False),                # strong, weak, exclude, ticker
    Column("source", String(48)),
    UniqueConstraint("instrument_id", "alias_norm", "kind", name="uq_alias"),
)
Index("ix_alias_norm", instrument_aliases.c.alias_norm)

provider_symbols = Table(
    "provider_symbols", metadata,
    Column("instrument_id", ID, ForeignKey("instruments.instrument_id", ondelete="CASCADE"), primary_key=True),
    Column("provider", String(32), primary_key=True),
    Column("provider_symbol", String(128), nullable=False),
    Column("priority", Integer, nullable=False, default=100),  # lower = preferred
    Column("verified_at", TS),
    Column("last_ok_at", TS),
    Column("last_error", Text),
)
Index("ix_provider_symbol_lookup", provider_symbols.c.provider, provider_symbols.c.provider_symbol)

listing_snapshots = Table(
    "listing_snapshots", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source", String(48), nullable=False),
    Column("fetched_at", TS, nullable=False),
    Column("row_count", Integer),
    Column("sha256", String(64)),
    Column("status", String(16), nullable=False),              # ok, failed, unchanged
    Column("note", Text),
)

provider_calls = Table(
    "provider_calls", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("provider", String(32), nullable=False),
    Column("endpoint", String(64), nullable=False),
    Column("status", String(24), nullable=False),              # ok, error, rate_limited, unavailable
    Column("http_status", Integer),
    Column("latency_ms", Float),
    Column("occurred_at", TS, nullable=False),
    Column("error", Text),
)
Index("ix_provider_calls_recent", provider_calls.c.provider, provider_calls.c.occurred_at)

prices = Table(
    "prices", metadata,
    Column("instrument_id", ID, nullable=False),
    Column("interval", String(8), nullable=False),             # 1d
    Column("ts", TS, nullable=False),                          # bar start, UTC
    Column("open", Float), Column("high", Float), Column("low", Float), Column("close", Float),
    Column("adj_close", Float), Column("volume", Float),
    Column("value", Float),                                    # NAV / yield / reference rate when there is no OHLC
    Column("provider", String(32), nullable=False),
    Column("provider_symbol", String(128)),
    Column("currency", String(12)),
    Column("timezone", String(48)),
    Column("adjusted", Boolean, nullable=False, default=False),
    Column("quality", String(16), nullable=False, default="ok"),
    Column("retrieved_at", TS, nullable=False),
    UniqueConstraint("instrument_id", "interval", "ts", "provider", name="uq_price_bar"),
)
Index("ix_prices_lookup", prices.c.instrument_id, prices.c.interval, prices.c.ts)

news = Table(
    "news", metadata,
    Column("news_id", String(40), primary_key=True),
    Column("headline", Text, nullable=False), Column("summary", Text), Column("source", Text), Column("url", Text),
    Column("published_at", TS, nullable=False),
    Column("provider", String(32), nullable=False),
    Column("fetched_at", TS, nullable=False),
)
Index("ix_news_published", news.c.published_at)

news_links = Table(
    "news_links", metadata,
    Column("news_id", String(40), ForeignKey("news.news_id", ondelete="CASCADE"), primary_key=True),
    Column("instrument_id", ID, primary_key=True),
    Column("entity_match_confidence", Float, nullable=False),
    Column("mapping_method", String(32), nullable=False),
)
Index("ix_news_links_instrument", news_links.c.instrument_id)

sentiment = Table(
    "sentiment", metadata,
    Column("news_id", String(40), ForeignKey("news.news_id", ondelete="CASCADE"), primary_key=True),
    Column("label", String(12), nullable=False),
    Column("positive_probability", Float), Column("neutral_probability", Float), Column("negative_probability", Float),
    Column("sentiment_score", Float), Column("confidence", Float),
    Column("model", String(64), nullable=False), Column("model_version", String(64)),
    Column("analysed_at", TS, nullable=False),
)

analysis_runs = Table(
    "analysis_runs", metadata,
    Column("run_id", String(96), primary_key=True),
    Column("instrument_id", ID, nullable=False),
    Column("created_at", TS, nullable=False),
    Column("pipeline_version", String(24), nullable=False),
    Column("feature_set_version", String(64)),
    Column("data_through", TS),
    Column("data_source", JSON), Column("models", JSON), Column("parameters", JSON),
    Column("result", JSON, nullable=False),
)
Index("ix_runs_instrument", analysis_runs.c.instrument_id, analysis_runs.c.created_at)

fingerprints = Table(
    "fingerprints", metadata,
    Column("run_id", String(96), primary_key=True),
    Column("instrument_id", ID, nullable=False),
    Column("as_of", TS),
    Column("version", String(64), nullable=False),
    Column("score", Float), Column("level", String(32)),
    Column("dimensions", JSON),
)

anomalies = Table(
    "anomalies", metadata,
    Column("anomaly_id", String(120), primary_key=True),
    Column("run_id", String(96), nullable=False),
    Column("instrument_id", ID, nullable=False),
    Column("ts", TS, nullable=False),
    Column("statistical_score", Float), Column("fingerprint_score", Float), Column("ml_score", Float),
    Column("anomaly_score", Float), Column("severity", String(12)),
    Column("detail", JSON),
)
Index("ix_anomalies_instrument", anomalies.c.instrument_id, anomalies.c.ts)

events = Table(
    "events", metadata,
    Column("event_id", String(120), primary_key=True),
    Column("anomaly_id", String(120), nullable=False),
    Column("instrument_id", ID, nullable=False),
    Column("start_time", TS), Column("end_time", TS),
    Column("correlation_score", Float),
    Column("detail", JSON),
)
Index("ix_events_instrument", events.c.instrument_id, events.c.start_time)
Index("ix_events_anomaly", events.c.anomaly_id)

risks = Table(
    "risks", metadata,
    Column("assessment_id", String(130), primary_key=True),
    Column("anomaly_id", String(120), nullable=False),
    Column("instrument_id", ID, nullable=False),
    Column("risk_score", Float), Column("risk_level", String(12)),
    Column("components", JSON),
    Column("created_at", TS, nullable=False),
)

evidence = Table(
    "evidence", metadata,
    Column("anomaly_id", String(120), primary_key=True),
    Column("seq", Integer, primary_key=True),
    Column("ts", TS), Column("type", String(24)), Column("description", Text), Column("value", Float),
    Column("source", Text), Column("linked_url", Text), Column("provenance", JSON),
)

jobs = Table(
    "jobs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("type", String(32), nullable=False),
    Column("instrument_id", ID),
    Column("dedupe_key", String(160)),
    Column("status", String(16), nullable=False),              # queued, running, done, failed
    Column("priority", Integer, nullable=False, default=100),
    Column("attempts", Integer, nullable=False, default=0),
    Column("max_attempts", Integer, nullable=False, default=3),
    Column("run_after", TS, nullable=False),
    Column("locked_by", String(64)), Column("locked_at", TS),
    Column("payload", JSON), Column("result", JSON), Column("error", Text),
    Column("created_at", TS, nullable=False), Column("updated_at", TS, nullable=False),
)
Index("ix_jobs_ready", jobs.c.status, jobs.c.run_after, jobs.c.priority)
Index("ix_jobs_dedupe", jobs.c.dedupe_key, jobs.c.status)

watchlists = Table(
    "watchlists", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(64), nullable=False, unique=True),
    Column("items", JSON, nullable=False),                     # ordered list of instrument_ids
    Column("is_default", Boolean, nullable=False, default=False),
    Column("updated_at", TS, nullable=False),
)


def database_url() -> str:
    """AVENTRA_DATABASE_URL (e.g. postgresql+psycopg://user:pass@db/aventra) or SQLite at AVENTRA_DB_PATH."""
    url = os.getenv("AVENTRA_DATABASE_URL", "").strip()
    if url:
        return url
    path = Path(config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}"


@lru_cache(maxsize=8)
def _engine_for(url: str) -> Engine:
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"timeout": 30, "check_same_thread": False}, future=True)

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):   # WAL + FK enforcement for SQLite
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        return engine
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5, future=True)


def dispose_engines() -> None:
    """Close every pooled connection (tests on Windows cannot delete SQLite files that are still open)."""
    for url in list(_opened_urls):
        _engine_for(url).dispose()
    _opened_urls.clear()
    _engine_for.cache_clear()


_opened_urls: set[str] = set()


def get_engine() -> Engine:
    _opened_urls.add(database_url())
    return _engine_for(database_url())


def is_postgres(engine: Engine | None = None) -> bool:
    return (engine or get_engine()).dialect.name == "postgresql"


def ensure_schema(engine: Engine | None = None) -> None:
    """Create missing tables directly (tests and fresh SQLite files). Real databases are upgraded with Alembic."""
    metadata.create_all(engine or get_engine())
