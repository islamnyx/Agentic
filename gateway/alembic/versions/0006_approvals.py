"""Approvals table (Phase 4)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("tool_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("parameters_hash", sa.String(64), nullable=False),
        sa.Column("parameters_json", sa.Text(), nullable=False),
        sa.Column("delegation_chain", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("approver_id", sa.String(36), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_approvals_agent_id"), "approvals", ["agent_id"], unique=False)
    op.create_index(op.f("ix_approvals_tool_id"), "approvals", ["tool_id"], unique=False)
    op.create_index(
        op.f("ix_approvals_parameters_hash"), "approvals", ["parameters_hash"], unique=False
    )
    op.create_index(op.f("ix_approvals_status"), "approvals", ["status"], unique=False)
    op.create_index(op.f("ix_approvals_approver_id"), "approvals", ["approver_id"], unique=False)
    op.create_index(op.f("ix_approvals_expires_at"), "approvals", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_approvals_expires_at"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_approver_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_status"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_parameters_hash"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_tool_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_agent_id"), table_name="approvals")
    op.drop_table("approvals")
