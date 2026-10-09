"""guardian consent for minor athletes

Revision ID: 7d3e9c1a5f42
Revises: 9c2f1a4b7d30
Create Date: 2026-10-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '7d3e9c1a5f42'
down_revision: Union[str, None] = '9c2f1a4b7d30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('consent_records', sa.Column('athlete_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_consent_athlete', 'consent_records', 'athletes', ['athlete_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_consent_records_athlete_id', 'consent_records', ['athlete_id'])
    op.add_column('consent_records', sa.Column('details', sa.JSON(), server_default=sa.text("'{}'"), nullable=False))


def downgrade() -> None:
    op.drop_column('consent_records', 'details')
    op.drop_index('ix_consent_records_athlete_id', table_name='consent_records')
    op.drop_constraint('fk_consent_athlete', 'consent_records', type_='foreignkey')
    op.drop_column('consent_records', 'athlete_id')
