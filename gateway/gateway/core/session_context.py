"""Session context service (Phase 6).

Manages session trust labels and provides helpers for session-aware policy evaluation.
"""

import json
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.models.session_context import SessionAwareRule, SessionContext, TrustLabel


class SessionContextService:
    """Service for managing session trust labels and session-aware rules."""

    def __init__(self) -> None:
        pass

    async def get_or_create_session(
        self,
        db: AsyncSession,
        session_id: str,
        agent_id: str,
        organization_id: str,
        initial_labels: list[str] | None = None,
    ) -> SessionContext:
        """Get existing session context or create new one."""
        result = await db.execute(
            select(SessionContext).where(SessionContext.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            return session

        labels = initial_labels or [TrustLabel.INTERNAL]
        new_session = SessionContext(
            session_id=session_id,
            agent_id=agent_id,
            organization_id=organization_id,
            labels=json.dumps(labels),
            current_label=TrustLabel.INTERNAL,
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return new_session

    async def add_label_to_session(
        self,
        db: AsyncSession,
        session_id: str,
        label: str,
    ) -> SessionContext | None:
        """Add a trust label to a session. Returns updated session or None if not found."""
        result = await db.execute(
            select(SessionContext).where(SessionContext.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return None

        labels = session.get_labels()
        if label not in labels:
            labels.append(label)
        session.labels = json.dumps(labels)

        # Update current_label to most untrusted
        trust_order = [TrustLabel.INTERNAL, TrustLabel.CUSTOMER_SUPPLIED, TrustLabel.WEB]
        for t in trust_order:
            if t in labels:
                session.current_label = t
                break

        await db.commit()
        await db.refresh(session)
        return session

    async def get_session_labels(self, db: AsyncSession, session_id: str) -> list[str]:
        """Get all trust labels for a session."""
        result = await db.execute(
            select(SessionContext).where(SessionContext.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return [TrustLabel.INTERNAL]
        return session.get_labels()

    async def get_current_session_label(self, db: AsyncSession, session_id: str) -> str:
        """Get the current (most untrusted) label for a session."""
        result = await db.execute(
            select(SessionContext).where(SessionContext.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return TrustLabel.INTERNAL
        return session.current_label

    async def evaluate_session_rules(
        self,
        db: AsyncSession,
        session_id: str,
        tool: str,
        action: str,
        resource_type: str,
    ) -> tuple[str, list[str]] | None:
        """Evaluate session-aware rules for a tool invocation.

        Returns (action, reasons) if a rule matches, else None.
        action: "require_approval", "deny", "allow"
        """
        session = await self._get_session(db, session_id)
        if not session:
            return None

        labels = session.get_labels()
        current_label = session.current_label

        # Get active session rules ordered by priority
        result = await db.execute(
            select(SessionAwareRule)
            .where(SessionAwareRule.is_active == True)
            .order_by(SessionAwareRule.priority.desc())
        )
        rules = result.scalars().all()

        for rule in rules:
            condition = json.loads(rule.condition)
            if self._matches_condition(condition, labels, current_label, tool, action, resource_type):
                return rule.action, [f"session rule: {rule.name}"]

        return None

    def _matches_condition(
        self,
        condition: dict[str, Any],
        labels: list[str],
        current_label: str,
        tool: str,
        action: str,
        resource_type: str,
    ) -> bool:
        """Check if a session rule condition matches."""
        # Check session label condition
        if "session_label" in condition:
            if condition["session_label"] not in labels:
                return False

        # Check tool category
        if "tool_category" in condition:
            if not self._tool_matches_category(tool, condition["tool_category"]):
                return False

        # Check action
        if "action" in condition:
            if action != condition["action"]:
                return False

        # Check resource type
        if "resource_type" in condition:
            if resource_type != condition["resource_type"]:
                return False

        return True

    def _tool_matches_category(self, tool: str, category: str) -> bool:
        """Check if tool matches a category."""
        external_categories = {
            "email": ["email", "smtp"],
            "web": ["http", "webhook", "playwright", "browser"],
            "database": ["postgres", "sql"],
        }
        if category in external_categories:
            return any(cat in tool.lower() for cat in external_categories[category])
        return False

    async def _get_session(
        self, db: AsyncSession, session_id: str
    ) -> SessionContext | None:
        result = await db.execute(
            select(SessionContext).where(SessionContext.session_id == session_id)
        )
        return result.scalar_one_or_none()


_session_context_service: Optional[SessionContextService] = None


def get_session_context_service() -> SessionContextService:
    global _session_context_service
    if _session_context_service is None:
        _session_context_service = SessionContextService()
    return _session_context_service