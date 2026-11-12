"""Pydantic schemas for business metrics (Phase 5)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DashboardMetricBase(BaseModel):
    metric_name: str
    metric_value: float
    metric_unit: Optional[str] = None
    organization_id: Optional[str] = None


class DashboardMetricCreate(DashboardMetricBase):
    pass


class DashboardMetricResponse(DashboardMetricBase):
    id: UUID
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SecurityIncidentBase(BaseModel):
    incident_type: str
    severity: str
    description: Optional[str] = None
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    organization_id: Optional[str] = None


class SecurityIncidentCreate(SecurityIncidentBase):
    pass


class SecurityIncidentResponse(SecurityIncidentBase):
    id: UUID
    detected_at: datetime
    resolved: bool
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AgentCostBase(BaseModel):
    agent_id: str
    organization_id: Optional[str] = None
    cost_type: str
    amount: float
    currency: Optional[str] = "USD"


class AgentCostCreate(AgentCostBase):
    pass


class AgentCostResponse(AgentCostBase):
    id: UUID
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)
