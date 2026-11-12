"""User model."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    role: Mapped[str] = mapped_column(sa.String(50), default="user")
    organization_id: Mapped[str] = mapped_column(sa.String(36), sa.ForeignKey("organizations.id"), nullable=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")
    owned_agents: Mapped[list["Agent"]] = relationship("Agent", back_populates="owner")
    knowledge_grants: Mapped[list["KnowledgeAccess"]] = relationship(
        "KnowledgeAccess", back_populates="granted_by_user"
    )
    approvals: Mapped[list["Approval"]] = relationship("Approval", back_populates="approver")
