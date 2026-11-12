"""Connector credentials and credential leases (Phase 3)

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-07 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "connector_credentials",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("connector_type", sa.String(50), nullable=False),
        sa.Column("encrypted_envelope", sa.Text(), nullable=False),
        sa.Column("key_id", sa.String(255), nullable=True),
        sa.Column(
            "kek_source", sa.String(20), nullable=False, server_default="local"
        ),
        sa.Column(
            "organization_id", sa.String(36), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_connector_credentials_name"), "connector_credentials", ["name"], unique=False)
    op.create_index(
        op.f("ix_connector_credentials_connector_type"),
        "connector_credentials",
        ["connector_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_connector_credentials_organization_id"),
        "connector_credentials",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "credential_leases",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("credential_id", sa.String(36), nullable=False),
        sa.Column("connector_type", sa.String(50), nullable=False),
        sa.Column("scope", sa.String(100), nullable=False, server_default="execute"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ),
        sa.ForeignKeyConstraint(["credential_id"], ["connector_credentials.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_credential_leases_agent_id"), "credential_leases", ["agent_id"], unique=False)
    op.create_index(
        op.f("ix_credential_leases_credential_id"), "credential_leases", ["credential_id"], unique=False
    )
    op.create_index(
        op.f("ix_credential_leases_connector_type"),
        "credential_leases",
        ["connector_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_credential_leases_connector_type"), table_name="credential_leases")
    op.drop_index(op.f("ix_credential_leases_credential_id"), table_name="credential_leases")
    op.drop_index(op.f("ix_credential_leases_agent_id"), table_name="credential_leases")
    op.drop_table("credential_leases")

    op.drop_index(op.f("ix_connector_credentials_organization_id"), table_name="connector_credentials")
    op.drop_index(op.f("ix_connector_credentials_connector_type"), table_name="connector_credentials")
    op.drop_index(op.f("ix_connector_credentials_name"), table_name="connector_credentials")
    op.drop_table("connector_credentials")
