"""Session context and trust labels (Phase 6)

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-10 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "data_labels",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False, index=True),
        sa.Column("resource_id", sa.String(36), nullable=False, index=True),
        sa.Column("label", sa.String(30), nullable=False, index=True),
        sa.Column("assigned_by", sa.String(36), nullable=False),
        sa.Column(
            "assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("metadata", sa.Text, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_data_labels_resource"), "data_labels", ["resource_type", "resource_id"], unique=False
    )

    op.create_table(
        "session_contexts",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("agent_id", sa.String(36), nullable=False, index=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("labels", sa.Text, nullable=False),
        sa.Column("current_label", sa.String(30), nullable=False, server_default="internal"),
        sa.Column("metadata", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "session_aware_rules",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("condition", sa.Text, nullable=False),
        sa.Column("action", sa.String(30), nullable=False, server_default="require_approval"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("session_aware_rules")
    op.drop_table("session_contexts")
    op.drop_index(op.f("ix_data_labels_resource"), table_name="data_labels")
    op.drop_table("data_labels")