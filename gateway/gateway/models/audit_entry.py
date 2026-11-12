"""Hash-chained audit log model (Phase 5).

Each audit entry is chained to the previous one via a SHA-256 hash so that
tampering with any row (editing, deleting, reordering) breaks the chain and
is detectable by the verify CLI.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from gateway.db.base import Base


class AuditEntry(Base):
    """A single tamper-evident audit log entry."""

    __tablename__ = "audit_entries"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    sequence: Mapped[int] = mapped_column(sa.Integer, nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    action: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(sa.String(36), nullable=True)
    actor_type: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(sa.String(36), nullable=True)
    details: Mapped[str | None] = mapped_column(sa.Text, nullable=True)  # JSON
    prev_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False, index=True)

    # Ed25519 signed roots (periodic)
    signed_root: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    @staticmethod
    def compute_hash(
        sequence: int,
        timestamp: str,
        action: str,
        actor_id: str | None,
        resource_type: str | None,
        resource_id: str | None,
        details: str | None,
        prev_hash: str,
    ) -> str:
        """Compute the SHA-256 hash for an audit entry."""
        canonical = json.dumps(
            {
                "sequence": sequence,
                "timestamp": timestamp,
                "action": action,
                "actor_id": actor_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details,
                "prev_hash": prev_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def genesis_hash() -> str:
        """Hash of the genesis (first) entry's previous hash."""
        return hashlib.sha256(b"genesis").hexdigest()
