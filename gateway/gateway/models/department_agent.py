"""Department agent assignment model."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class DepartmentAgent(Base):
    __tablename__ = "department_agents"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("agents.id"), nullable=False, index=True
    )
    department_id: Mapped[str | None] = mapped_column(
        sa.String(36), sa.ForeignKey("departments.id"), nullable=True, index=True
    )
    team_id: Mapped[str | None] = mapped_column(
        sa.String(36), sa.ForeignKey("teams.id"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(sa.String(50), default="specialist")
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    agent: Mapped["Agent"] = relationship("Agent")
    department: Mapped["Department | None"] = relationship(
        "Department", back_populates="members", foreign_keys=[department_id]
    )
    team: Mapped["Team | None"] = relationship(
        "Team", back_populates="members", foreign_keys=[team_id]
    )
