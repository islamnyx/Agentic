"""Pydantic schemas for approvals (Phase 4)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ApprovalResponse(BaseModel):
    id: UUID
    agent_id: str
    tool_id: str
    action: str
    parameters_hash: str
    status: str
    approver_id: Optional[str] = None
    decided_at: Optional[datetime] = None
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalAction(BaseModel):
    """Approve or deny a pending approval."""

    reason: Optional[str] = None


class ApprovalList(BaseModel):
    items: list[ApprovalResponse]
