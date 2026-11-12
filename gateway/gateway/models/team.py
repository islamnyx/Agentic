"""Team model."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    department_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("departments.id"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    department: Mapped["Department"] = relationship("Department", back_populates="teams")
    organization: Mapped["Organization"] = relationship("Organization")
    members: Mapped[list["DepartmentAgent"]] = relationship(
        "DepartmentAgent", back_populates="team"
    )
