"""Tool call log model."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_id: Mapped[str] = mapped_column(sa.String(36), sa.ForeignKey("agents.id"), nullable=False, index=True)
    tool_id: Mapped[str] = mapped_column(sa.String(36), sa.ForeignKey("tools.id"), nullable=False, index=True)
    parameters: Mapped[str | None] = mapped_column(sa.Text, nullable=True)  # JSON string
    result: Mapped[str | None] = mapped_column(sa.Text, nullable=True)  # JSON string
    decision: Mapped[str] = mapped_column(sa.String(50), default="pending")  # allowed, denied, require_approval
    decision_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    agent: Mapped["Agent"] = relationship("Agent", back_populates="tool_calls")
    tool: Mapped["Tool"] = relationship("Tool", back_populates="tool_calls")
