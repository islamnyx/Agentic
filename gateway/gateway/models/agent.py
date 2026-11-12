"""Agent model."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    scopes: Mapped[str] = mapped_column(sa.Text, default="")  # comma-separated scopes
    revoked_at: Mapped[sa.DateTime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    organization_id: Mapped[str] = mapped_column(sa.String(36), sa.ForeignKey("organizations.id"), nullable=False)
    owner_id: Mapped[str] = mapped_column(sa.String(36), sa.ForeignKey("users.id"), nullable=False)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="agents")
    owner: Mapped["User"] = relationship("User", back_populates="owned_agents")
    tokens: Mapped[list["AgentToken"]] = relationship("AgentToken", back_populates="agent")
    tool_calls: Mapped[list["ToolCall"]] = relationship("ToolCall", back_populates="agent")
    department_assignments: Mapped[list["DepartmentAgent"]] = relationship(
        "DepartmentAgent", back_populates="agent"
    )
    credential_leases: Mapped[list["CredentialLease"]] = relationship(
        "CredentialLease", back_populates="agent"
    )
    approvals: Mapped[list["Approval"]] = relationship("Approval", back_populates="agent")

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def scope_list(self) -> list[str]:
        if not self.scopes:
            return []
        return [s.strip() for s in self.scopes.split(",") if s.strip()]
