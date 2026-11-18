"""admin console: patient last seen, push device user agent

Revision ID: c3d9e1f2a7b4
Revises: b7c41d2e9a10
Create Date: 2026-11-19 01:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d9e1f2a7b4'
down_revision: Union[str, None] = 'b7c41d2e9a10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('patients', sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('push_subscriptions', sa.Column('user_agent', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('push_subscriptions', 'user_agent')
    op.drop_column('patients', 'last_seen_at')
