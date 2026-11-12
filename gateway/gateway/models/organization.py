"""Organization model."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    users: Mapped[list["User"]] = relationship("User", back_populates="organization")
    agents: Mapped[list["Agent"]] = relationship("Agent", back_populates="organization")
    departments: Mapped[list["Department"]] = relationship(
        "Department", back_populates="organization"
    )
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="organization")
    knowledge_items: Mapped[list["KnowledgeItem"]] = relationship(
        "KnowledgeItem", back_populates="organization"
    )
