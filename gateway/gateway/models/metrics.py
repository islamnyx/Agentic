"""Business metrics models (Phase 5).

Tables feeding the Control Center dashboards:
* ``dashboard_metrics`` - key/value metrics (work completed, pending approvals,
  failed tasks, security incidents, agent costs).
* ``security_incidents`` - detected security events (audit tampering, SSRF
  blocks, policy denials, approval violations).
* ``agent_costs`` - per-agent cost tracking.
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from gateway.db.base import Base


class DashboardMetric(Base):
    """A single business/dashboad metric sample."""

    __tablename__ = "dashboard_metrics"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    metric_name: Mapped[str] = mapped_column(
        sa.String(100), nullable=False, index=True
    )
    metric_value: Mapped[float] = mapped_column(sa.Float(), nullable=False)
    metric_unit: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(
        sa.String(36), nullable=True, index=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


class SecurityIncident(Base):
    """A detected security incident."""

    __tablename__ = "security_incidents"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    incident_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, index=True
    )  # e.g. audit_tampering, ssrf_block, policy_denied, approval_violation
    severity: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, index=True
    )  # low | medium | high | critical
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    actor_id: Mapped[str | None] = mapped_column(
        sa.String(36), nullable=True, index=True
    )
    actor_type: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(sa.String(36), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(
        sa.String(36), nullable=True, index=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    resolved: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.false(), index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[str | None] = mapped_column(sa.String(36), nullable=True)


class AgentCost(Base):
    """Per-agent cost sample."""

    __tablename__ = "agent_costs"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_id: Mapped[str] = mapped_column(
        sa.String(36), nullable=False, index=True
    )
    organization_id: Mapped[str | None] = mapped_column(
        sa.String(36), nullable=True, index=True
    )
    cost_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, index=True
    )  # e.g. tool_call, mcp_call, secret_access
    amount: Mapped[float] = mapped_column(sa.Float(), nullable=False)
    currency: Mapped[str] = mapped_column(
        sa.String(10), nullable=False, server_default="USD"
    )
    recorded_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
