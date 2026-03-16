"""add runtime turn fields

Revision ID: 20260310_0008
Revises: 20260310_0007
Create Date: 2026-03-10 14:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260310_0008"
down_revision = "20260310_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("call_turns", sa.Column("response_audio_ref", sa.String(length=255), nullable=True))
    op.add_column("call_turns", sa.Column("finish_reason", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("call_turns", "finish_reason")
    op.drop_column("call_turns", "response_audio_ref")
