"""Business metrics routes (Phase 5).

Endpoints for recording and querying the Control Center business metrics:
dashboard metrics, security incidents, and agent costs.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.api.deps import get_current_agent, get_db
from gateway.models.metrics import AgentCost, DashboardMetric, SecurityIncident
from gateway.schemas.metrics import (
    AgentCostCreate,
    AgentCostResponse,
    DashboardMetricCreate,
    DashboardMetricResponse,
    SecurityIncidentCreate,
    SecurityIncidentResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Dashboard metrics
# ---------------------------------------------------------------------------


@router.post(
    "/metrics/dashboard",
    response_model=DashboardMetricResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_dashboard_metric(
    body: DashboardMetricCreate,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Record a dashboard metric sample."""
    org_id = body.organization_id or str(current_agent.organization_id)
    metric = DashboardMetric(
        metric_name=body.metric_name,
        metric_value=body.metric_value,
        metric_unit=body.metric_unit,
        organization_id=org_id,
    )
    db.add(metric)
    await db.commit()
    await db.refresh(metric)
    return metric


@router.get("/metrics/dashboard", response_model=list[DashboardMetricResponse])
async def list_dashboard_metrics(
    metric_name: Optional[str] = Query(None),
    organization_id: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """List dashboard metric samples, newest first."""
    query = select(DashboardMetric).order_by(
        DashboardMetric.recorded_at.desc()
    )
    if metric_name:
        query = query.where(DashboardMetric.metric_name == metric_name)
    if organization_id:
        query = query.where(DashboardMetric.organization_id == organization_id)
    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Security incidents
# ---------------------------------------------------------------------------


@router.post(
    "/metrics/security-incidents",
    response_model=SecurityIncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_security_incident(
    body: SecurityIncidentCreate,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Record a detected security incident."""
    org_id = body.organization_id or str(current_agent.organization_id)
    incident = SecurityIncident(
        incident_type=body.incident_type,
        severity=body.severity,
        description=body.description,
        actor_id=body.actor_id or str(current_agent.id),
        actor_type=body.actor_type or "agent",
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        organization_id=org_id,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return incident


@router.get("/metrics/security-incidents", response_model=list[SecurityIncidentResponse])
async def list_security_incidents(
    incident_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    organization_id: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """List security incidents, newest first."""
    query = select(SecurityIncident).order_by(SecurityIncident.detected_at.desc())
    if incident_type:
        query = query.where(SecurityIncident.incident_type == incident_type)
    if severity:
        query = query.where(SecurityIncident.severity == severity)
    if resolved is not None:
        query = query.where(SecurityIncident.resolved == resolved)
    if organization_id:
        query = query.where(SecurityIncident.organization_id == organization_id)
    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/metrics/security-incidents/{incident_id}/resolve")
async def resolve_security_incident(
    incident_id: str,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Mark a security incident as resolved."""
    result = await db.execute(
        select(SecurityIncident).where(SecurityIncident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found"
        )
    incident.resolved = True
    incident.resolved_at = datetime.now(timezone.utc)
    incident.resolved_by = str(current_agent.id)
    await db.commit()
    return {"id": incident_id, "resolved": True}


# ---------------------------------------------------------------------------
# Agent costs
# ---------------------------------------------------------------------------


@router.post(
    "/metrics/agent-costs",
    response_model=AgentCostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_agent_cost(
    body: AgentCostCreate,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Record a per-agent cost sample."""
    org_id = body.organization_id or str(current_agent.organization_id)
    cost = AgentCost(
        agent_id=body.agent_id,
        organization_id=org_id,
        cost_type=body.cost_type,
        amount=body.amount,
        currency=body.currency or "USD",
    )
    db.add(cost)
    await db.commit()
    await db.refresh(cost)
    return cost


@router.get("/metrics/agent-costs", response_model=list[AgentCostResponse])
async def list_agent_costs(
    agent_id: Optional[str] = Query(None),
    cost_type: Optional[str] = Query(None),
    organization_id: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """List agent cost samples, newest first."""
    query = select(AgentCost).order_by(AgentCost.recorded_at.desc())
    if agent_id:
        query = query.where(AgentCost.agent_id == agent_id)
    if cost_type:
        query = query.where(AgentCost.cost_type == cost_type)
    if organization_id:
        query = query.where(AgentCost.organization_id == organization_id)
    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
