"""Connector credential and lease models (Phase 3).

ConnectorCredential stores an envelope-encrypted secret for a connector type
(HTTP basic auth, PostgreSQL password, SMTP credentials, MCP token, etc.).
The raw secret is never stored in plaintext.

CredentialLease records short-lived, scoped leases issued by the credential
broker. Agents present a lease to obtain the decrypted secret for connector
execution; they never receive the raw secret themselves.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class ConnectorCredential(Base):
    """Envelope-encrypted credential for a connector type."""

    __tablename__ = "connector_credentials"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False, index=True)
    connector_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False
    )  # http, postgres, smtp, mcp, playwright
    encrypted_envelope: Mapped[str] = mapped_column(
        sa.Text, nullable=False
    )  # JSON string: {ciphertext, nonce, wrapped_dek, key_id, kek_source}
    key_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    kek_source: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, server_default="local"
    )  # vault | local
    organization_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    organization: Mapped["Organization"] = relationship("Organization")
    leases: Mapped[list["CredentialLease"]] = relationship(
        "CredentialLease", back_populates="credential"
    )


class CredentialLease(Base):
    """Short-lived, scoped lease to a connector credential."""

    __tablename__ = "credential_leases"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("agents.id"), nullable=False, index=True
    )
    credential_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("connector_credentials.id"), nullable=False, index=True
    )
    connector_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    scope: Mapped[str] = mapped_column(
        sa.String(100), nullable=False, server_default="execute"
    )  # e.g. "execute", "read", "send"
    expires_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    used_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    agent: Mapped["Agent"] = relationship("Agent", back_populates="credential_leases")
    credential: Mapped["ConnectorCredential"] = relationship(
        "ConnectorCredential", back_populates="leases"
    )

    @property
    def is_expired(self) -> bool:
        from datetime import datetime, timezone

        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp <= datetime.now(timezone.utc)

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.is_revoked and self.used_at is None
