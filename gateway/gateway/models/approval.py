"""Approval model (Phase 4).

Records human approval decisions for tool invocations that require approval
(e.g. high-risk refunds, discounts, email campaigns, record deletion).

An approval is bound to the exact parameters of the invocation via a SHA-256
hash of the parameter set, plus the full delegation chain context (who
requested, which agent, session, org, owner). It supports a lifecycle of:
pending → approved|denied|expired, with single-use enforcement (an approved
approval is consumed on execution and cannot be reused).
"""

import hashlib
import json
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class Approval(Base):
    """Human approval decision for a gated tool invocation."""

    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("agents.id"), nullable=False, index=True
    )
    tool_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("tools.id"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    parameters_hash: Mapped[str] = mapped_column(
        sa.String(64), nullable=False, index=True
    )  # sha256 of canonical parameters
    parameters_json: Mapped[str] = mapped_column(sa.Text, nullable=False)
    delegation_chain: Mapped[str] = mapped_column(
        sa.Text, nullable=False
    )  # JSON: agent, session, org, owner
    status: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default="pending", index=True
    )  # pending | approved | denied | expired | used
    approver_id: Mapped[str | None] = mapped_column(
        sa.String(36), sa.ForeignKey("users.id"), nullable=True, index=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    agent: Mapped["Agent"] = relationship("Agent", back_populates="approvals")
    tool: Mapped["Tool"] = relationship("Tool", back_populates="approvals")
    approver: Mapped["User | None"] = relationship("User")

    @property
    def is_expired(self) -> bool:
        from datetime import datetime, timezone

        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp <= datetime.now(timezone.utc)

    @property
    def is_decided(self) -> bool:
        return self.status in ("approved", "denied", "expired", "used")

    @property
    def is_usable(self) -> bool:
        """True only if approved, not expired, and not yet consumed."""
        return (
            self.status == "approved"
            and not self.is_expired
        )

    @staticmethod
    def hash_parameters(parameters: dict) -> str:
        """SHA-256 hash of canonical (sorted) parameters — binds approval to
        the exact parameter set."""
        canonical = json.dumps(parameters, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
