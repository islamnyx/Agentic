"""Business metrics tables (Phase 5)

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-08 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dashboard_metrics",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False, index=True),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("metric_unit", sa.String(30), nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=True, index=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_dashboard_metrics_recorded_at"),
        "dashboard_metrics",
        ["recorded_at"],
        unique=False,
    )

    op.create_table(
        "security_incidents",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("incident_type", sa.String(50), nullable=False, index=True),
        sa.Column("severity", sa.String(20), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.String(36), nullable=True, index=True),
        sa.Column("actor_type", sa.String(50), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=True, index=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false(), index=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_security_incidents_detected_at"),
        "security_incidents",
        ["detected_at"],
        unique=False,
    )

    op.create_table(
        "agent_costs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("agent_id", sa.String(36), nullable=False, index=True),
        sa.Column("organization_id", sa.String(36), nullable=True, index=True),
        sa.Column("cost_type", sa.String(50), nullable=False, index=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("agent_costs")
    op.drop_table("security_incidents")
    op.drop_table("dashboard_metrics")
