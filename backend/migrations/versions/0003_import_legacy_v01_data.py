"""Copy v0.1 data into the new schema, keyed by canonical instrument IDs (legacy tables are kept untouched).

- legacy news / news_links / news_sentiment → news / news_links / sentiment (real Google News headlines and
  their FinBERT outputs). v0.1 symbols map to NSE listings: RELIANCE → XNSE:RELIANCE.
- legacy prices → prices with provider `yahoo_finance_chart` preserved as provenance. The store never serves
  these rows to users (store.LEGACY_EXCLUDED_PROVIDERS, Phase 0 decision C22); they remain for reproducibility.
- Synthetic DEMO rows are not copied. Legacy analysis results (pipeline v0.1) stay only in legacy_* tables.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-27
"""
from alembic import op
import pandas as pd
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _ts(value):
    if value in (None, ""):
        return None
    ts = pd.Timestamp(value)
    return (ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")).to_pydatetime()


def _iid(symbol: str) -> str:
    return f"XNSE:{symbol.upper()}"


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    if "legacy_news" not in existing:
        return
    meta = sa.MetaData()
    news, links, sentiment, prices = (sa.Table(name, meta, autoload_with=bind) for name in ("news", "news_links", "sentiment", "prices"))
    legacy_news = sa.Table("legacy_news", meta, autoload_with=bind)
    demo_ids = {row.news_id for row in bind.execute(sa.select(legacy_news.c.news_id).where(legacy_news.c.is_demo == 1))}

    rows = [{"news_id": r.news_id, "headline": r.headline, "summary": r.summary, "source": r.source, "url": r.url, "published_at": _ts(r.published_at),
             "provider": r.provider, "fetched_at": _ts(r.fetched_at)} for r in bind.execute(sa.select(legacy_news)) if r.news_id not in demo_ids]
    if rows:
        bind.execute(sa.insert(news), rows)
    if "legacy_news_links" in existing:
        legacy_links = sa.Table("legacy_news_links", meta, autoload_with=bind)
        rows = [{"news_id": r.news_id, "instrument_id": _iid(r.symbol), "entity_match_confidence": r.entity_match_confidence, "mapping_method": r.mapping_method}
                for r in bind.execute(sa.select(legacy_links)) if r.news_id not in demo_ids and r.symbol.upper() != "DEMO"]
        if rows:
            bind.execute(sa.insert(links), rows)
    if "legacy_news_sentiment" in existing:
        legacy_sent = sa.Table("legacy_news_sentiment", meta, autoload_with=bind)
        rows = [{"news_id": r.news_id, "label": r.label, "positive_probability": r.positive_probability, "neutral_probability": r.neutral_probability,
                 "negative_probability": r.negative_probability, "sentiment_score": r.sentiment_score, "confidence": r.confidence, "model": r.model,
                 "model_version": r.model_version, "analysed_at": _ts(r.analysed_at)} for r in bind.execute(sa.select(legacy_sent)) if r.news_id not in demo_ids]
        if rows:
            bind.execute(sa.insert(sentiment), rows)
    if "legacy_prices" in existing:
        legacy_prices = sa.Table("legacy_prices", meta, autoload_with=bind)
        rows = [{"instrument_id": _iid(r.symbol), "interval": "1d", "ts": _ts(r.timestamp), "open": r.open, "high": r.high, "low": r.low, "close": r.close,
                 "adj_close": r.adj_close, "volume": r.volume, "value": None, "provider": r.source, "provider_symbol": f"{r.symbol}.NS", "currency": "INR",
                 "timezone": "Asia/Kolkata", "adjusted": False, "quality": "legacy", "retrieved_at": _ts(r.fetched_at)}
                for r in bind.execute(sa.select(legacy_prices)) if r.symbol.upper() != "DEMO"]
        for start in range(0, len(rows), 1000):
            bind.execute(sa.insert(prices), rows[start:start + 1000])


def downgrade() -> None:
    bind = op.get_bind()
    meta = sa.MetaData()
    for name in ("sentiment", "news_links", "news"):
        bind.execute(sa.delete(sa.Table(name, meta, autoload_with=bind)))
    prices = sa.Table("prices", meta, autoload_with=bind)
    bind.execute(sa.delete(prices).where(prices.c.quality == "legacy"))
