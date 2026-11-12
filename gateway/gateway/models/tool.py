"""Tool model."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    connector_type: Mapped[str] = mapped_column(sa.String(50), default="native")  # native, mcp, http, postgres, smtp, playwright
    config: Mapped[str | None] = mapped_column(sa.Text, nullable=True)  # JSON string with connector config
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    tool_calls: Mapped[list["ToolCall"]] = relationship("ToolCall", back_populates="tool")
    approvals: Mapped[list["Approval"]] = relationship("Approval", back_populates="tool")
