"""public FIE identity and ranking snapshot on athletes

Revision ID: b4e8a1c92d10
Revises: 7d3e9c1a5f42
Create Date: 2026-10-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b4e8a1c92d10"
down_revision: Union[str, None] = "7d3e9c1a5f42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("athletes", sa.Column("fie_id", sa.Integer(), nullable=True))
    op.add_column("athletes", sa.Column("fie_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("athletes", sa.Column("fie_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index(
        "uq_athlete_org_fie",
        "athletes",
        ["organization_id", "fie_id"],
        unique=True,
        postgresql_where=sa.text("fie_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_athlete_org_fie", table_name="athletes")
    op.drop_column("athletes", "fie_profile")
    op.drop_column("athletes", "fie_synced_at")
    op.drop_column("athletes", "fie_id")
