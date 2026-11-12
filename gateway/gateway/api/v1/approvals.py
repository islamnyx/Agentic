"""Approval routes (Phase 4).

Human approval flow for tool invocations that require approval:

* ``GET /v1/approvals/pending`` — approver queue: lists pending approvals
* ``POST /v1/approvals/{id}/approve`` — approve a pending approval
* ``POST /v1/approvals/{id}/deny`` — deny a pending approval
* ``GET /v1/approvals/{id}`` — get approval details

An approval is bound to the exact invocation parameters (via a SHA-256 hash)
and the full delegation chain context. It supports a lifecycle of
pending → approved|denied|expired with single-use enforcement.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.api.deps import get_current_agent, get_db
from gateway.models.agent import Agent
from gateway.models.approval import Approval
from gateway.schemas.approval import ApprovalAction, ApprovalList, ApprovalResponse

router = APIRouter()

DEFAULT_APPROVAL_TTL_SECONDS = 3600  # 1 hour


@router.get("/approvals/pending", response_model=ApprovalList)
async def list_pending_approvals(
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Approver queue: list all pending, non-expired approvals."""
    result = await db.execute(
        select(Approval).where(
            Approval.status == "pending",
            Approval.expires_at > datetime.now(timezone.utc),
        )
    )
    return ApprovalList(items=result.scalars().all())


@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Get approval details."""
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found"
        )
    return approval


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_approval(
    approval_id: str,
    action_in: ApprovalAction = ApprovalAction(),
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending approval.

    The approver must belong to the same organization as the requesting agent.
    """
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found"
        )
    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval is already {approval.status}",
        )
    if approval.is_expired:
        approval.status = "expired"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approval has expired",
        )

    # Verify the requesting agent's org matches the approval's agent org.
    result = await db.execute(
        select(Agent).where(Agent.id == approval.agent_id)
    )
    requesting_agent = result.scalar_one_or_none()
    if not requesting_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Requesting agent not found"
        )
    if str(current_agent.organization_id) != str(requesting_agent.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot approve an approval from another organization",
        )

    now = datetime.now(timezone.utc)
    approval.status = "approved"
    approval.approver_id = current_agent.id
    approval.decided_at = now
    await db.commit()
    await db.refresh(approval)
    return approval


@router.post("/approvals/{approval_id}/deny", response_model=ApprovalResponse)
async def deny_approval(
    approval_id: str,
    action_in: ApprovalAction = ApprovalAction(),
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Deny a pending approval."""
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found"
        )
    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval is already {approval.status}",
        )
    if approval.is_expired:
        approval.status = "expired"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approval has expired",
        )

    result = await db.execute(
        select(Agent).where(Agent.id == approval.agent_id)
    )
    requesting_agent = result.scalar_one_or_none()
    if not requesting_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Requesting agent not found"
        )
    if str(current_agent.organization_id) != str(requesting_agent.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deny an approval from another organization",
        )

    now = datetime.now(timezone.utc)
    approval.status = "denied"
    approval.approver_id = current_agent.id
    approval.decided_at = now
    await db.commit()
    await db.refresh(approval)
    return approval
