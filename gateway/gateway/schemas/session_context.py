"""Pydantic schemas for trust labels and session context (Phase 6)."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TrustLabel(str, Enum):
    INTERNAL = "internal"
    CUSTOMER_SUPPLIED = "customer-supplied"
    WEB = "web"


class DataLabelBase(BaseModel):
    resource_type: str
    resource_id: str
    label: TrustLabel


class DataLabelCreate(DataLabelBase):
    pass


class DataLabelResponse(DataLabelBase):
    id: UUID
    assigned_by: str
    assigned_at: datetime
    metadata: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class SessionContextBase(BaseModel):
    session_id: str
    agent_id: str
    organization_id: str
    labels: list[TrustLabel] = Field(default_factory=list)
    current_label: TrustLabel = TrustLabel.INTERNAL
    metadata: Optional[dict[str, Any]] = None


class SessionContextCreate(SessionContextBase):
    pass


class SessionContextUpdate(BaseModel):
    labels: Optional[list[TrustLabel]] = None
    current_label: Optional[TrustLabel] = None
    metadata: Optional[dict[str, Any]] = None


class SessionContextResponse(SessionContextBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class SessionAwareRuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    condition: dict[str, Any]
    action: str = "require_approval"
    priority: int = 100
    is_active: bool = True


class SessionAwareRuleCreate(SessionAwareRuleBase):
    pass


class SessionAwareRuleUpdate(BaseModel):
    description: Optional[str] = None
    condition: Optional[dict[str, Any]] = None
    action: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class SessionAwareRuleResponse(SessionAwareRuleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)