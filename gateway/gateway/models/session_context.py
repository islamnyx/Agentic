"""Trust label and session context models (Phase 6).

Provides:
* DataLabel - persistent labels on knowledge items, tool parameters, and other resources
* SessionContext - carries trust labels through multi-step agent sessions
* SessionAwareRule - session-aware policy rules (untrusted -> external send -> require_approval)
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gateway.db.base import Base


class TrustLabel(str, Enum):
    """Trust levels for data provenance."""

    INTERNAL = "internal"
    CUSTOMER_SUPPLIED = "customer-supplied"
    WEB = "web"


class DataLabel(Base):
    """Persistent trust label on a resource (knowledge item, tool parameter, etc.)."""

    __tablename__ = "data_labels"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    resource_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, index=True
    )  # knowledge_item, tool_parameter, session, file, etc.
    resource_id: Mapped[str] = mapped_column(sa.String(36), nullable=False, index=True)
    label: Mapped[str] = mapped_column(sa.String(30), nullable=False, index=True)
    assigned_by: Mapped[str] = mapped_column(sa.String(36), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    label_metadata: Mapped[Optional[str]] = mapped_column("metadata", sa.Text, nullable=True)  # JSON

    __table_args__ = (
        sa.Index("ix_data_labels_resource", "resource_type", "resource_id"),
    )


class SessionContext(Base):
    """Session-scoped context carrying trust labels through multi-step operations."""

    __tablename__ = "session_contexts"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True, index=True)
    agent_id: Mapped[str] = mapped_column(sa.String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(sa.String(36), nullable=False, index=True)
    # Accumulated trust labels in this session (JSON array of labels)
    labels: Mapped[str] = mapped_column(sa.Text, nullable=False)  # JSON array of TrustLabel values
    # Last seen label (most recent/untrusted)
    current_label: Mapped[str] = mapped_column(sa.String(30), nullable=False, default=TrustLabel.INTERNAL)
    # Metadata for the session
    session_metadata: Mapped[Optional[str]] = mapped_column("metadata", sa.Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False
    )

    def get_labels(self) -> list[str]:
        import json
        return json.loads(self.labels) if self.labels else []

    def add_label(self, label: str) -> None:
        import json
        labels = self.get_labels()
        if label not in labels:
            labels.append(label)
        self.labels = json.dumps(labels)
        # Update current_label to the most untrusted label (check from most to least)
        trust_order = [TrustLabel.WEB, TrustLabel.CUSTOMER_SUPPLIED, TrustLabel.INTERNAL]
        for t in trust_order:
            if t in labels:
                self.current_label = t
                break


class SessionAwareRule(Base):
    """Configurable session-aware policy rules.

    Example: "untrusted content in session -> external send -> require_approval"
    """

    __tablename__ = "session_aware_rules"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    # Condition: JSON describing when the rule applies
    # Example: {"session_label": "web", "tool_category": "external", "action": "write"}
    condition: Mapped[str] = mapped_column(sa.Text, nullable=False)  # JSON
    # Action: what to do when condition matches
    # Values: "require_approval", "deny", "allow"
    action: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="require_approval")
    # Priority for rule evaluation (higher = evaluated first)
    priority: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False
    )