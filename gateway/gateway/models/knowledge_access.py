"""Company Brain knowledge access (ACL) model."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class KnowledgeAccess(Base):
    __tablename__ = "knowledge_access"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    knowledge_item_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("knowledge_items.id"), nullable=False, index=True
    )
    department_id: Mapped[str | None] = mapped_column(
        sa.String(36), sa.ForeignKey("departments.id"), nullable=True, index=True
    )
    team_id: Mapped[str | None] = mapped_column(
        sa.String(36), sa.ForeignKey("teams.id"), nullable=True, index=True
    )
    agent_id: Mapped[str | None] = mapped_column(
        sa.String(36), sa.ForeignKey("agents.id"), nullable=True, index=True
    )
    permission: Mapped[str] = mapped_column(sa.String(20), default="read")
    granted_by: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    knowledge_item: Mapped["KnowledgeItem"] = relationship(
        "KnowledgeItem", back_populates="access_grants"
    )
    department: Mapped["Department | None"] = relationship("Department", foreign_keys=[department_id])
    team: Mapped["Team | None"] = relationship("Team", foreign_keys=[team_id])
    agent: Mapped["Agent | None"] = relationship("Agent", foreign_keys=[agent_id])
    granted_by_user: Mapped["User"] = relationship("User", foreign_keys=[granted_by])
