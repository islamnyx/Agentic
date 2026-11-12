"""Department model."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    organization_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True
    )
    manager_agent_id: Mapped[str | None] = mapped_column(
        sa.String(36), sa.ForeignKey("agents.id"), nullable=True, index=True
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    organization: Mapped["Organization"] = relationship("Organization")
    manager_agent: Mapped["Agent | None"] = relationship("Agent", foreign_keys=[manager_agent_id])
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="department")
    members: Mapped[list["DepartmentAgent"]] = relationship(
        "DepartmentAgent", back_populates="department"
    )
