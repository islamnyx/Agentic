"""Session context and trust label routes (Phase 6)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.api.deps import get_current_agent, get_db
from gateway.models.agent import Agent
from gateway.models.session_context import DataLabel, SessionAwareRule, SessionContext, TrustLabel
from gateway.schemas.session_context import (
    DataLabelCreate,
    DataLabelResponse,
    SessionAwareRuleCreate,
    SessionAwareRuleResponse,
    SessionContextCreate,
    SessionContextResponse,
    SessionContextUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Data Labels
# ---------------------------------------------------------------------------


@router.post(
    "/labels",
    response_model=DataLabelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_data_label(
    body: DataLabelCreate,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Assign a trust label to a resource."""
    label = DataLabel(
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        label=body.label,
        assigned_by=str(current_agent.id),
    )
    if body.metadata is not None:
        label.label_metadata = json.dumps(body.metadata) if isinstance(body.metadata, dict) else str(body.metadata)
    db.add(label)
    await db.commit()
    await db.refresh(label)
    return label


@router.get("/labels", response_model=list[DataLabelResponse])
async def list_data_labels(
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    label: Optional[TrustLabel] = Query(None),
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """List data labels."""
    query = select(DataLabel)
    if resource_type:
        query = query.where(DataLabel.resource_type == resource_type)
    if resource_id:
        query = query.where(DataLabel.resource_id == resource_id)
    if label:
        query = query.where(DataLabel.label == label)
    result = await db.execute(query)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Session Context
# ---------------------------------------------------------------------------


@router.post(
    "/sessions",
    response_model=SessionContextResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_context(
    body: SessionContextCreate,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Create a new session context with initial trust labels."""
    import json

    session = SessionContext(
        session_id=body.session_id,
        agent_id=body.agent_id,
        organization_id=body.organization_id,
        labels=json.dumps([l.value if hasattr(l, 'value') else l for l in body.labels]),
        current_label=body.current_label.value if hasattr(body.current_label, 'value') else body.current_label,
        session_metadata=json.dumps(body.metadata) if body.metadata else None,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}", response_model=SessionContextResponse)
async def get_session_context(
    session_id: str,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Get session context."""
    result = await db.execute(
        select(SessionContext).where(SessionContext.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session context not found"
        )
    return session


@router.patch("/sessions/{session_id}", response_model=SessionContextResponse)
async def update_session_context(
    session_id: str,
    body: SessionContextUpdate,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Update session context (add labels, update current_label, etc.)."""
    import json

    result = await db.execute(
        select(SessionContext).where(SessionContext.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session context not found"
        )

    if body.labels is not None:
        session.labels = json.dumps(body.labels)
        # Update current_label to most untrusted
        trust_order = [TrustLabel.INTERNAL, TrustLabel.CUSTOMER_SUPPLIED, TrustLabel.WEB]
        for t in trust_order:
            if t in body.labels:
                session.current_label = t
                break

    if body.current_label is not None:
        session.current_label = body.current_label

    if body.metadata is not None:
        session.session_metadata = json.dumps(body.metadata)

    await db.commit()
    await db.refresh(session)
    return session


# ---------------------------------------------------------------------------
# Session-Aware Rules
# ---------------------------------------------------------------------------


@router.post(
    "/session-rules",
    response_model=SessionAwareRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_rule(
    body: SessionAwareRuleCreate,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Create a session-aware policy rule."""
    import json

    rule = SessionAwareRule(
        name=body.name,
        description=body.description,
        condition=json.dumps(body.condition),
        action=body.action,
        priority=body.priority,
        is_active=body.is_active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/session-rules", response_model=list[SessionAwareRuleResponse])
async def list_session_rules(
    is_active: Optional[bool] = Query(None),
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """List session-aware rules."""
    query = select(SessionAwareRule).order_by(SessionAwareRule.priority.desc())
    if is_active is not None:
        query = query.where(SessionAwareRule.is_active == is_active)
    result = await db.execute(query)
    return result.scalars().all()