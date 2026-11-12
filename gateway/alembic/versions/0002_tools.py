"""Tool registry tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tools",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("connector_type", sa.String(50), nullable=False, server_default="native"),
        sa.Column("config", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tools_name"), "tools", ["name"], unique=True)

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("tool_id", sa.String(36), nullable=False),
        sa.Column("parameters", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tool_calls_agent_id"), "tool_calls", ["agent_id"], unique=False)
    op.create_index(op.f("ix_tool_calls_tool_id"), "tool_calls", ["tool_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tool_calls_tool_id"), table_name="tool_calls")
    op.drop_index(op.f("ix_tool_calls_agent_id"), table_name="tool_calls")
    op.drop_table("tool_calls")
    op.drop_index(op.f("ix_tools_name"), table_name="tools")
    op.drop_table("tools")
