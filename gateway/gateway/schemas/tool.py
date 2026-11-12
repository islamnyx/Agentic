"""Pydantic schemas for tools and tool invocation."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ToolCreate(BaseModel):
    name: str
    description: Optional[str] = None
    connector_type: str = "native"
    config: Optional[str] = None
    is_active: bool = True


class ToolResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    connector_type: str
    config: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ToolInvokeRequest(BaseModel):
    parameters: dict[str, Any] = {}
    lease_token: Optional[str] = None


class ToolInvokeResponse(BaseModel):
    decision: str
    reason: str
    result: Optional[dict[str, Any]] = None
    tool_call_id: UUID
