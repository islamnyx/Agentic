"""Agent token model."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class AgentToken(Base):
    __tablename__ = "agent_tokens"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_id: Mapped[str] = mapped_column(sa.String(36), sa.ForeignKey("agents.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    expires_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[sa.DateTime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    agent: Mapped["Agent"] = relationship("Agent", back_populates="tokens")

    @property
    def is_expired(self) -> bool:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None
