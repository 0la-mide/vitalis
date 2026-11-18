"""triage channel (ussd)

Revision ID: b7c41d2e9a10
Revises: f552a4876e40
Create Date: 2026-11-18 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7c41d2e9a10'
down_revision: Union[str, None] = 'f552a4876e40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('triage_reports', sa.Column('channel', sa.String(length=8), nullable=True))


def downgrade() -> None:
    op.drop_column('triage_reports', 'channel')
