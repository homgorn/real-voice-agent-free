"""add calls tables

Revision ID: 20260309_0003
Revises: 20260309_0002
Create Date: 2026-03-09 20:45:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260309_0003"
down_revision = "20260309_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calls",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("agent_id", sa.String(length=32), nullable=False),
        sa.Column("phone_number_id", sa.String(length=32), nullable=True),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("from_number", sa.String(length=32), nullable=False),
        sa.Column("to_number", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("recording_available", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_calls_agent_id"), "calls", ["agent_id"], unique=False)

    op.create_table(
        "call_turns",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("call_id", sa.String(length=32), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("user_text", sa.Text(), nullable=False),
        sa.Column("assistant_text", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("provider_breakdown", sa.JSON(), nullable=False),
        sa.Column("tool_calls", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_call_turns_call_id"), "call_turns", ["call_id"], unique=False)

    op.create_table(
        "call_summaries",
        sa.Column("call_id", sa.String(length=32), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("structured_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("call_id"),
    )


def downgrade() -> None:
    op.drop_table("call_summaries")
    op.drop_index(op.f("ix_call_turns_call_id"), table_name="call_turns")
    op.drop_table("call_turns")
    op.drop_index(op.f("ix_calls_agent_id"), table_name="calls")
    op.drop_table("calls")
