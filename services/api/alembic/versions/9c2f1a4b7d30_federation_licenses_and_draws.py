"""federation licenses, entries, and draw metadata

Revision ID: 9c2f1a4b7d30
Revises: 47a49b674fe6
Create Date: 2026-10-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '9c2f1a4b7d30'
down_revision: Union[str, None] = '47a49b674fe6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('athletes', sa.Column('license_number', sa.String(length=40), server_default='', nullable=False))
    op.add_column('athletes', sa.Column('birth_year', sa.Integer(), nullable=True))
    op.add_column('athletes', sa.Column('category', sa.String(length=16), server_default='unspecified', nullable=False))
    op.create_index(
        'uq_athlete_org_license',
        'athletes',
        ['organization_id', 'license_number'],
        unique=True,
        postgresql_where=sa.text("license_number <> ''"),
    )
    op.create_table(
        'competition_entries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('competition_id', sa.UUID(), nullable=False),
        sa.Column('athlete_id', sa.UUID(), nullable=False),
        sa.Column('seed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['competition_id'], ['competitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('competition_id', 'athlete_id', name='uq_competition_athlete'),
    )
    op.create_index('ix_competition_entries_organization_id', 'competition_entries', ['organization_id'])
    op.create_index('ix_competition_entries_competition_id', 'competition_entries', ['competition_id'])
    op.create_index('ix_competition_entries_athlete_id', 'competition_entries', ['athlete_id'])
    op.add_column('bouts', sa.Column('round', sa.String(length=24), server_default='', nullable=False))
    op.add_column('bouts', sa.Column('bracket_label', sa.String(length=120), server_default='', nullable=False))
    op.add_column('bouts', sa.Column('referee_user_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_bouts_referee', 'bouts', 'users', ['referee_user_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_bouts_referee', 'bouts', type_='foreignkey')
    op.drop_column('bouts', 'referee_user_id')
    op.drop_column('bouts', 'bracket_label')
    op.drop_column('bouts', 'round')
    op.drop_index('ix_competition_entries_athlete_id', table_name='competition_entries')
    op.drop_index('ix_competition_entries_competition_id', table_name='competition_entries')
    op.drop_index('ix_competition_entries_organization_id', table_name='competition_entries')
    op.drop_table('competition_entries')
    op.drop_index('uq_athlete_org_license', table_name='athletes')
    op.drop_column('athletes', 'category')
    op.drop_column('athletes', 'birth_year')
    op.drop_column('athletes', 'license_number')
