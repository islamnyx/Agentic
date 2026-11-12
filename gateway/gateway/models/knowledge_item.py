"""Company Brain knowledge item model."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    category: Mapped[str] = mapped_column(
        sa.String(100), nullable=False, server_default="internal"
    )
    department_id: Mapped[str | None] = mapped_column(
        sa.String(36), sa.ForeignKey("departments.id"), nullable=True, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True
    )
    is_confidential: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    department: Mapped["Department | None"] = relationship("Department", foreign_keys=[department_id])
    organization: Mapped["Organization"] = relationship("Organization")
    access_grants: Mapped[list["KnowledgeAccess"]] = relationship(
        "KnowledgeAccess", back_populates="knowledge_item"
    )
