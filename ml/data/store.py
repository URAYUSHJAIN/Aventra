"""Persistence layer (SQLAlchemy Core; PostgreSQL or SQLite). Parameterised statements only.

All rows are keyed by canonical `instrument_id`. Timestamps are stored in UTC. Schema lives in ml/data/db.py and
is created/upgraded by Alembic (backend/migrations); tests may call `db.ensure_schema()` on a fresh file.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Iterable

import pandas as pd
from sqlalchemy import and_, delete, func, insert, select, update

from ml.data import db

# Providers whose stored rows may be served to users. Rows from other providers (e.g. the v0.1 Yahoo data kept for
# provenance) stay in the database but are never used as production data (Phase 0 decision, AGENTS.md C22).
LEGACY_EXCLUDED_PROVIDERS = {"yahoo_finance_chart", "aventra_demo_dataset"}
LEGACY_EXCLUDED_NEWS_PROVIDERS = {"google_news_rss"}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


def utc(value) -> datetime | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    ts = pd.Timestamp(value)
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    return ts.to_pydatetime()


def iso(value) -> str | None:
    dt = utc(value)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def _num(value):
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(value) or math.isinf(value) else value


def _upsert(conn, table, rows: list[dict], keys: list[str], update_cols: Iterable[str] | None = None) -> None:
    """INSERT … ON CONFLICT (keys) DO UPDATE/NOTHING for PostgreSQL and SQLite."""
    if not rows:
        return
    # PostgreSQL rejects a statement that touches the same conflict key twice; keep the last row per key (SQLite's behaviour).
    rows = list({tuple(row.get(k) for k in keys): row for row in rows}.values())
    if conn.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    else:
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    update_cols = list(update_cols) if update_cols is not None else [c.name for c in table.columns if c.name not in keys]
    for start in range(0, len(rows), 500):
        stmt = dialect_insert(table).values(rows[start:start + 500])
        if update_cols:
            stmt = stmt.on_conflict_do_update(index_elements=keys, set_={col: stmt.excluded[col] for col in update_cols})
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=keys)
        conn.execute(stmt)


def begin():
    return db.get_engine().begin()


# ============================================================ instruments
def upsert_instruments(rows: list[dict], aliases: list[dict] | None = None, provider_rows: list[dict] | None = None,
                       keep_manual_fields: bool = True) -> int:
    """Insert/refresh instruments with their aliases and provider mappings in one transaction."""
    stamp = now_utc()
    prepared = []
    for row in rows:
        prepared.append({**{c.name: None for c in db.instruments.columns}, "status": "listed", **row, "created_at": row.get("created_at") or stamp, "updated_at": stamp})
    # popularity is maintained separately (set_popularity) and must survive a listing re-sync.
    update_cols = [c.name for c in db.instruments.columns if c.name not in {"instrument_id", "created_at", "popularity"}]
    with begin() as conn:
        _upsert(conn, db.instruments, prepared, ["instrument_id"], update_cols)
        if aliases:
            _upsert(conn, db.instrument_aliases, [{k: a[k] for k in ("instrument_id", "alias", "alias_norm", "kind", "source")} for a in aliases],
                    ["instrument_id", "alias_norm", "kind"], [])
        if provider_rows:
            _upsert(conn, db.provider_symbols, provider_rows, ["instrument_id", "provider"], ["provider_symbol", "priority"])
    return len(prepared)


def get_instrument(instrument_id: str) -> dict | None:
    with db.get_engine().connect() as conn:
        row = conn.execute(select(db.instruments).where(db.instruments.c.instrument_id == instrument_id)).mappings().first()
        if not row:
            return None
        result = dict(row)
        result["aliases"] = [dict(r) for r in conn.execute(select(db.instrument_aliases.c.alias, db.instrument_aliases.c.kind)
                                                          .where(db.instrument_aliases.c.instrument_id == instrument_id)).mappings()]
        result["providers"] = [dict(r) for r in conn.execute(select(db.provider_symbols).where(db.provider_symbols.c.instrument_id == instrument_id)
                                                            .order_by(db.provider_symbols.c.priority)).mappings()]
    return result


def instruments_by_ids(ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    with db.get_engine().connect() as conn:
        rows = conn.execute(select(db.instruments).where(db.instruments.c.instrument_id.in_(ids))).mappings().all()
    return {row["instrument_id"]: dict(row) for row in rows}


def find_by_provider_symbol(provider: str, provider_symbol: str) -> str | None:
    with db.get_engine().connect() as conn:
        return conn.execute(select(db.provider_symbols.c.instrument_id).where(and_(db.provider_symbols.c.provider == provider,
                                                                                  db.provider_symbols.c.provider_symbol == provider_symbol))).scalar()


def mark_provider_symbol(instrument_id: str, provider: str, ok: bool, error: str | None = None) -> None:
    values = {"last_ok_at": now_utc(), "last_error": None} if ok else {"last_error": (error or "")[:500]}
    with begin() as conn:
        conn.execute(update(db.provider_symbols).where(and_(db.provider_symbols.c.instrument_id == instrument_id,
                                                            db.provider_symbols.c.provider == provider)).values(**values))


def set_instrument_fields(instrument_id: str, **fields) -> None:
    with begin() as conn:
        conn.execute(update(db.instruments).where(db.instruments.c.instrument_id == instrument_id).values(**fields, updated_at=now_utc()))


def set_popularity(values: dict[str, float]) -> None:
    with begin() as conn:
        for instrument_id, rank in values.items():
            conn.execute(update(db.instruments).where(db.instruments.c.instrument_id == instrument_id).values(popularity=rank))


def classifications(source_prefix: str) -> dict[str, tuple[str, str, float]]:
    """instrument_id → (asset_class, class_source, class_confidence) for refined classifications (kept across re-syncs)."""
    with db.get_engine().connect() as conn:
        rows = conn.execute(select(db.instruments.c.instrument_id, db.instruments.c.asset_class, db.instruments.c.class_source, db.instruments.c.class_confidence)
                            .where(db.instruments.c.class_source.like(f"{source_prefix}%"))).all()
    return {r[0]: (r[1], r[2], r[3]) for r in rows}


def count_instruments(**filters) -> int:
    stmt = select(func.count()).select_from(db.instruments)
    for key, value in filters.items():
        stmt = stmt.where(getattr(db.instruments.c, key) == value)
    with db.get_engine().connect() as conn:
        return int(conn.execute(stmt).scalar() or 0)


def record_listing_snapshot(source: str, row_count: int, sha256: str | None, status: str, note: str | None = None) -> None:
    with begin() as conn:
        conn.execute(insert(db.listing_snapshots).values(source=source, fetched_at=now_utc(), row_count=row_count, sha256=sha256, status=status, note=note))


def last_listing_snapshot(source: str) -> dict | None:
    with db.get_engine().connect() as conn:
        row = conn.execute(select(db.listing_snapshots).where(and_(db.listing_snapshots.c.source == source, db.listing_snapshots.c.status == "ok"))
                           .order_by(db.listing_snapshots.c.fetched_at.desc()).limit(1)).mappings().first()
    return dict(row) if row else None


def record_provider_call(provider: str, endpoint: str, status: str, http_status: int | None, latency_ms: float | None, error: str | None = None) -> None:
    with begin() as conn:
        conn.execute(insert(db.provider_calls).values(provider=provider, endpoint=endpoint[:64], status=status, http_status=http_status,
                                                      latency_ms=latency_ms, occurred_at=now_utc(), error=(error or None) and error[:500]))


def provider_call_stats(provider: str, since: datetime) -> dict:
    with db.get_engine().connect() as conn:
        rows = conn.execute(select(db.provider_calls.c.status, func.count()).where(and_(db.provider_calls.c.provider == provider,
                                                                                         db.provider_calls.c.occurred_at >= since))
                            .group_by(db.provider_calls.c.status)).all()
    return {status: int(count) for status, count in rows}


# ============================================================ prices
def upsert_prices(frame: pd.DataFrame) -> int:
    """frame columns: instrument_id, interval, timestamp, open, high, low, close, adj_close, volume, value, provider,
    provider_symbol, currency, timezone, adjusted, quality."""
    if frame.empty:
        return 0
    stamp = now_utc()
    rows = [{
        "instrument_id": r.instrument_id, "interval": getattr(r, "interval", "1d"), "ts": utc(r.timestamp),
        "open": _num(getattr(r, "open", None)), "high": _num(getattr(r, "high", None)), "low": _num(getattr(r, "low", None)),
        "close": _num(getattr(r, "close", None)), "adj_close": _num(getattr(r, "adj_close", None)), "volume": _num(getattr(r, "volume", None)),
        "value": _num(getattr(r, "value", None)), "provider": r.provider, "provider_symbol": getattr(r, "provider_symbol", None),
        "currency": getattr(r, "currency", None), "timezone": getattr(r, "timezone", None), "adjusted": bool(getattr(r, "adjusted", False)),
        "quality": getattr(r, "quality", "ok") or "ok", "retrieved_at": stamp,
    } for r in frame.itertuples(index=False)]
    with begin() as conn:
        _upsert(conn, db.prices, rows, ["instrument_id", "interval", "ts", "provider"])
    return len(rows)


def load_prices(instrument_id: str, interval: str = "1d", providers: set[str] | None = None) -> pd.DataFrame:
    """Stored bars for one instrument. Legacy/excluded providers are never returned unless explicitly requested."""
    stmt = select(db.prices).where(and_(db.prices.c.instrument_id == instrument_id, db.prices.c.interval == interval))
    if providers:
        stmt = stmt.where(db.prices.c.provider.in_(providers))
    else:
        from ml import config
        excluded = set(LEGACY_EXCLUDED_PROVIDERS)
        if config.synthetic_test_data_enabled():   # automated tests only
            excluded.discard("aventra_demo_dataset")
        stmt = stmt.where(db.prices.c.provider.notin_(excluded))
    with db.get_engine().connect() as conn:
        rows = conn.execute(stmt.order_by(db.prices.c.ts)).mappings().all()
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame([dict(r) for r in rows]).rename(columns={"ts": "timestamp"})
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["retrieved_at"] = pd.to_datetime(frame["retrieved_at"], utc=True)
    return frame


def latest_price_ts(instrument_id: str, provider: str, interval: str = "1d") -> datetime | None:
    with db.get_engine().connect() as conn:
        value = conn.execute(select(func.max(db.prices.c.ts)).where(and_(db.prices.c.instrument_id == instrument_id,
                                                                         db.prices.c.interval == interval, db.prices.c.provider == provider))).scalar()
    return utc(value)


# ============================================================ news + sentiment
def upsert_news(items: list[dict]) -> None:
    stamp = now_utc()
    news_rows, link_rows = [], []
    for item in items:
        news_rows.append({"news_id": item["news_id"], "headline": item["headline"], "summary": item.get("summary"), "source": item.get("source"),
                          "url": item.get("url"), "published_at": utc(item["published_at"]), "provider": item["provider"], "fetched_at": stamp})
        for link in item.get("links", []):
            link_rows.append({"news_id": item["news_id"], "instrument_id": link["instrument_id"],
                              "entity_match_confidence": link["entity_match_confidence"], "mapping_method": link["mapping_method"]})
    with begin() as conn:
        _upsert(conn, db.news, news_rows, ["news_id"], [])
        _upsert(conn, db.news_links, link_rows, ["news_id", "instrument_id"], ["entity_match_confidence", "mapping_method"])


def load_news(instrument_id: str | None = None, limit: int = 50) -> list[dict]:
    s, n, l = db.sentiment, db.news, db.news_links
    stmt = (select(n, l.c.instrument_id, l.c.entity_match_confidence, l.c.mapping_method, s.c.label, s.c.positive_probability, s.c.neutral_probability,
                   s.c.negative_probability, s.c.sentiment_score, s.c.confidence, s.c.model, s.c.model_version)
            .select_from(n.join(l, l.c.news_id == n.c.news_id).outerjoin(s, s.c.news_id == n.c.news_id)))
    if instrument_id:
        stmt = stmt.where(l.c.instrument_id == instrument_id)
    # v0.1 Google News RSS rows stay stored for provenance but are not served (robots.txt disallows /rss/search; AGENTS.md C23).
    stmt = stmt.where(n.c.provider.notin_(LEGACY_EXCLUDED_NEWS_PROVIDERS))
    with db.get_engine().connect() as conn:
        rows = conn.execute(stmt.order_by(n.c.published_at.desc()).limit(limit)).mappings().all()
    out = []
    for row in rows:
        item = dict(row)
        item["published_at"] = iso(item["published_at"])
        item["fetched_at"] = iso(item["fetched_at"])
        out.append(item)
    return out


def sentiment_for(news_ids: list[str]) -> dict[str, dict]:
    if not news_ids:
        return {}
    with db.get_engine().connect() as conn:
        rows = conn.execute(select(db.sentiment).where(db.sentiment.c.news_id.in_(news_ids))).mappings().all()
    return {row["news_id"]: dict(row) for row in rows}


def upsert_sentiment(results: dict[str, dict]) -> None:
    stamp = now_utc()
    rows = [{"news_id": news_id, "label": r["label"], "positive_probability": r["positive_probability"], "neutral_probability": r["neutral_probability"],
             "negative_probability": r["negative_probability"], "sentiment_score": r["sentiment_score"], "confidence": r["confidence"],
             "model": r["model"], "model_version": r.get("model_version"), "analysed_at": stamp} for news_id, r in results.items()]
    with begin() as conn:
        _upsert(conn, db.sentiment, rows, ["news_id"])


# ============================================================ analysis results
def save_run(result: dict) -> None:
    instrument_id, run_id = result["instrument_id"], result["run_id"]
    with begin() as conn:
        conn.execute(insert(db.analysis_runs).values(
            run_id=run_id, instrument_id=instrument_id, created_at=utc(result["generated_at"]), pipeline_version=result["pipeline_version"],
            feature_set_version=result.get("versions", {}).get("feature_set"), data_through=utc(result.get("market", {}).get("latest", {}).get("trading_date")),
            data_source=result.get("data_source"), models=result.get("models"), parameters=result.get("parameters"), result=result))
        fp = result.get("fingerprint") or {}
        conn.execute(insert(db.fingerprints).values(run_id=run_id, instrument_id=instrument_id, as_of=utc(fp.get("as_of")),
                                                     version=result.get("versions", {}).get("fingerprint", "unknown"), score=fp.get("score"),
                                                     level=fp.get("level"), dimensions=fp.get("dimensions")))
        for event in result.get("events", []):
            anomaly, risk = event["anomaly"], event["risk"]
            _upsert(conn, db.anomalies, [{"anomaly_id": anomaly["anomaly_id"], "run_id": run_id, "instrument_id": instrument_id, "ts": utc(anomaly["timestamp"]),
                                          "statistical_score": anomaly["scores"]["statistical"], "fingerprint_score": anomaly["scores"]["fingerprint"],
                                          "ml_score": anomaly["scores"]["isolation_forest"], "anomaly_score": anomaly["anomaly_score"],
                                          "severity": anomaly["severity"], "detail": anomaly}], ["anomaly_id"])
            _upsert(conn, db.events, [{"event_id": event["event_id"], "anomaly_id": anomaly["anomaly_id"], "instrument_id": instrument_id,
                                       "start_time": utc(event["window"]["start"]), "end_time": utc(event["window"]["end"]),
                                       "correlation_score": event["correlation"]["best_score"], "detail": event}], ["event_id"])
            _upsert(conn, db.risks, [{"assessment_id": f"RA-{anomaly['anomaly_id']}", "anomaly_id": anomaly["anomaly_id"], "instrument_id": instrument_id,
                                      "risk_score": risk["score"], "risk_level": risk["level"], "components": risk["components"],
                                      "created_at": utc(result["generated_at"])}], ["assessment_id"])
            conn.execute(delete(db.evidence).where(db.evidence.c.anomaly_id == anomaly["anomaly_id"]))
            rows = [{"anomaly_id": anomaly["anomaly_id"], "seq": seq, "ts": utc(item.get("timestamp")), "type": item["type"], "description": item["description"],
                     "value": _num(item.get("value")), "source": item["source"], "linked_url": item.get("url"), "provenance": item.get("provenance")}
                    for seq, item in enumerate(event["evidence"])]
            if rows:
                conn.execute(insert(db.evidence), rows)


def latest_run(instrument_id: str) -> dict | None:
    with db.get_engine().connect() as conn:
        row = conn.execute(select(db.analysis_runs.c.result).where(db.analysis_runs.c.instrument_id == instrument_id)
                           .order_by(db.analysis_runs.c.created_at.desc()).limit(1)).first()
    return row[0] if row else None


def get_event_by(column: str, value: str) -> dict | None:
    if column not in {"event_id", "anomaly_id"}:
        raise ValueError("Unsupported lookup column")
    with db.get_engine().connect() as conn:
        row = conn.execute(select(db.events.c.detail).where(getattr(db.events.c, column) == value).limit(1)).first()
    return row[0] if row else None


def list_anomalies(instrument_id: str | None = None, limit: int = 100) -> list[dict]:
    stmt = select(db.anomalies.c.detail)
    if instrument_id:
        stmt = stmt.where(db.anomalies.c.instrument_id == instrument_id)
    with db.get_engine().connect() as conn:
        return [row[0] for row in conn.execute(stmt.order_by(db.anomalies.c.ts.desc()).limit(limit))]


def list_events(instrument_id: str | None = None, limit: int = 100) -> list[dict]:
    stmt = select(db.events.c.detail)
    if instrument_id:
        stmt = stmt.where(db.events.c.instrument_id == instrument_id)
    with db.get_engine().connect() as conn:
        return [row[0] for row in conn.execute(stmt.order_by(db.events.c.start_time.desc()).limit(limit))]


# ============================================================ watchlists
def get_watchlist(name: str | None = None) -> dict | None:
    stmt = select(db.watchlists)
    stmt = stmt.where(db.watchlists.c.name == name) if name else stmt.where(db.watchlists.c.is_default.is_(True))
    with db.get_engine().connect() as conn:
        row = conn.execute(stmt.limit(1)).mappings().first()
    return dict(row) if row else None


def save_watchlist(name: str, items: list[str], is_default: bool = False) -> None:
    with begin() as conn:
        _upsert(conn, db.watchlists, [{"name": name, "items": items, "is_default": is_default, "updated_at": now_utc()}], ["name"])
