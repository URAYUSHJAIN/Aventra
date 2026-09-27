"""Preserve v0.1 tables: rename the symbol-keyed schema to legacy_* (no data is dropped).

Only acts when the old schema is present (a `prices` table with a `symbol` column), i.e. on databases created
by pipeline v0.1. Fresh databases are unaffected.

Revision ID: 0001
Revises:
Create Date: 2026-09-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

LEGACY_TABLES = ["prices", "news", "news_links", "news_sentiment", "pipeline_runs", "anomalies", "events", "risk_assessments", "evidence"]


def _has_v01_schema(inspector) -> bool:
    return "prices" in inspector.get_table_names() and "symbol" in {c["name"] for c in inspector.get_columns("prices")}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not _has_v01_schema(inspector):
        return
    existing = set(inspector.get_table_names())
    for table in LEGACY_TABLES:
        if table in existing:
            op.rename_table(table, f"legacy_{table}")
    if op.get_bind().dialect.name == "sqlite":
        # SQLite index names are database-global; drop v0.1 index names so the new schema can use its own.
        for index in ("idx_news_published", "idx_links_symbol", "idx_runs_symbol", "idx_anomalies_symbol"):
            op.execute(f"DROP INDEX IF EXISTS {index}")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names())
    for table in LEGACY_TABLES:
        if f"legacy_{table}" in existing and table not in existing:
            op.rename_table(f"legacy_{table}", table)
