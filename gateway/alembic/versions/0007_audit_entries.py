"""Audit entries table (Phase 5)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-08 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_entries",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("actor_type", sa.String(50), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("entry_hash", sa.String(64), nullable=False),
        sa.Column("signed_root", sa.Text(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_entries_sequence"), "audit_entries", ["sequence"], unique=False)
    op.create_index(op.f("ix_audit_entries_entry_hash"), "audit_entries", ["entry_hash"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_entries_entry_hash"), table_name="audit_entries")
    op.drop_index(op.f("ix_audit_entries_sequence"), table_name="audit_entries")
    op.drop_table("audit_entries")
