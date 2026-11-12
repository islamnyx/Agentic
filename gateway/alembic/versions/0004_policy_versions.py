"""Policy versions table

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-06 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "policy_versions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("policy_path", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_policy_versions_version"), "policy_versions", ["version"], unique=True)
    op.create_index(op.f("ix_policy_versions_active"), "policy_versions", ["active"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_policy_versions_active"), table_name="policy_versions")
    op.drop_index(op.f("ix_policy_versions_version"), table_name="policy_versions")
    op.drop_table("policy_versions")
