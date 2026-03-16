"""add organization scoping columns

Revision ID: 20260310_0005
Revises: 20260310_0004
Create Date: 2026-03-10 10:50:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260310_0005"
down_revision = "20260310_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("organization_id", sa.String(length=32), nullable=False, server_default="org_default"),
    )
    op.create_index(op.f("ix_agents_organization_id"), "agents", ["organization_id"], unique=False)

    op.add_column(
        "bookings",
        sa.Column("organization_id", sa.String(length=32), nullable=False, server_default="org_default"),
    )
    op.create_index(op.f("ix_bookings_organization_id"), "bookings", ["organization_id"], unique=False)

    op.add_column(
        "calls",
        sa.Column("organization_id", sa.String(length=32), nullable=False, server_default="org_default"),
    )
    op.create_index(op.f("ix_calls_organization_id"), "calls", ["organization_id"], unique=False)

    op.add_column(
        "webhook_subscriptions",
        sa.Column("organization_id", sa.String(length=32), nullable=False, server_default="org_default"),
    )
    op.create_index(
        op.f("ix_webhook_subscriptions_organization_id"),
        "webhook_subscriptions",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_webhook_subscriptions_organization_id"), table_name="webhook_subscriptions")
    op.drop_column("webhook_subscriptions", "organization_id")
    op.drop_index(op.f("ix_calls_organization_id"), table_name="calls")
    op.drop_column("calls", "organization_id")
    op.drop_index(op.f("ix_bookings_organization_id"), table_name="bookings")
    op.drop_column("bookings", "organization_id")
    op.drop_index(op.f("ix_agents_organization_id"), table_name="agents")
    op.drop_column("agents", "organization_id")
