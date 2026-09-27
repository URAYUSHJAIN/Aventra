"""Search quality: normalised search_text and an optional popularity rank on instruments.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("instruments") as batch:
        batch.add_column(sa.Column("search_text", sa.Text(), nullable=True))
        batch.add_column(sa.Column("popularity", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("instruments") as batch:
        batch.drop_column("popularity")
        batch.drop_column("search_text")
