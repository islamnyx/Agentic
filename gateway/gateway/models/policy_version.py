"""Policy version model (Phase 2: Policy Engine).

Stores each Rego policy version applied to the gateway so policy decisions are
auditable and rollback-capable.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from gateway.db.base import Base


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    version: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True, index=True)
    policy_path: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    # e.g. /v1/data/gateway/allow
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)  # Rego source
    active: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
