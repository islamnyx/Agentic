"""Departments, teams, department agents, and Company Brain tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Departments ---
    op.create_table(
        "departments",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "organization_id", sa.String(36), nullable=False
        ),
        sa.Column(
            "manager_agent_id", sa.String(36), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.ForeignKeyConstraint(["manager_agent_id"], ["agents.id"], ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_departments_name"), "departments", ["name"], unique=False)
    op.create_index(
        op.f("ix_departments_organization_id"), "departments", ["organization_id"], unique=False
    )

    # --- Teams ---
    op.create_table(
        "teams",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "department_id", sa.String(36), nullable=False
        ),
        sa.Column(
            "organization_id", sa.String(36), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_teams_name"), "teams", ["name"], unique=False)
    op.create_index(
        op.f("ix_teams_department_id"), "teams", ["department_id"], unique=False
    )
    op.create_index(
        op.f("ix_teams_organization_id"), "teams", ["organization_id"], unique=False
    )

    # --- Department agents (agent -> department/team assignment) ---
    op.create_table(
        "department_agents",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("department_id", sa.String(36), nullable=True),
        sa.Column("team_id", sa.String(36), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="specialist"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_department_agents_agent_id"), "department_agents", ["agent_id"], unique=False)
    op.create_index(
        op.f("ix_department_agents_department_id"), "department_agents", ["department_id"], unique=False
    )
    op.create_index(
        op.f("ix_department_agents_team_id"), "department_agents", ["team_id"], unique=False
    )

    # --- Company Brain knowledge items ---
    op.create_table(
        "knowledge_items",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=False, server_default="internal"),
        sa.Column("department_id", sa.String(36), nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("is_confidential", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_knowledge_items_title"), "knowledge_items", ["title"], unique=False)
    op.create_index(
        op.f("ix_knowledge_items_category"), "knowledge_items", ["category"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_items_organization_id"), "knowledge_items", ["organization_id"], unique=False
    )

    # --- Company Brain knowledge access (per-item ACLs) ---
    op.create_table(
        "knowledge_access",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("knowledge_item_id", sa.String(36), nullable=False),
        sa.Column("department_id", sa.String(36), nullable=True),
        sa.Column("team_id", sa.String(36), nullable=True),
        sa.Column("agent_id", sa.String(36), nullable=True),
        sa.Column("permission", sa.String(20), nullable=False, server_default="read"),
        sa.Column("granted_by", sa.String(36), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.ForeignKeyConstraint(["knowledge_item_id"], ["knowledge_items.id"], ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_access_knowledge_item_id"), "knowledge_access", ["knowledge_item_id"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_access_department_id"), "knowledge_access", ["department_id"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_access_team_id"), "knowledge_access", ["team_id"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_access_agent_id"), "knowledge_access", ["agent_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_knowledge_access_agent_id"), table_name="knowledge_access")
    op.drop_index(op.f("ix_knowledge_access_team_id"), table_name="knowledge_access")
    op.drop_index(op.f("ix_knowledge_access_department_id"), table_name="knowledge_access")
    op.drop_index(op.f("ix_knowledge_access_knowledge_item_id"), table_name="knowledge_access")
    op.drop_table("knowledge_access")

    op.drop_index(op.f("ix_knowledge_items_organization_id"), table_name="knowledge_items")
    op.drop_index(op.f("ix_knowledge_items_category"), table_name="knowledge_items")
    op.drop_index(op.f("ix_knowledge_items_title"), table_name="knowledge_items")
    op.drop_table("knowledge_items")

    op.drop_index(op.f("ix_department_agents_team_id"), table_name="department_agents")
    op.drop_index(op.f("ix_department_agents_department_id"), table_name="department_agents")
    op.drop_index(op.f("ix_department_agents_agent_id"), table_name="department_agents")
    op.drop_table("department_agents")

    op.drop_index(op.f("ix_teams_organization_id"), table_name="teams")
    op.drop_index(op.f("ix_teams_department_id"), table_name="teams")
    op.drop_index(op.f("ix_teams_name"), table_name="teams")
    op.drop_table("teams")

    op.drop_index(op.f("ix_departments_organization_id"), table_name="departments")
    op.drop_index(op.f("ix_departments_name"), table_name="departments")
    op.drop_table("departments")
