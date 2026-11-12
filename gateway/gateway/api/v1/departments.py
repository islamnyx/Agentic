"""Department and team routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.api.deps import get_db
from gateway.models.department import Department
from gateway.models.team import Team
from gateway.models.department_agent import DepartmentAgent
from gateway.schemas.department import (
    DepartmentAgentCreate,
    DepartmentAgentResponse,
    DepartmentCreate,
    DepartmentResponse,
    TeamCreate,
    TeamResponse,
)

router = APIRouter()


# --- Departments ---

@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    dept_in: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new department within an organization."""
    dept = Department(
        name=dept_in.name,
        organization_id=dept_in.organization_id,
        manager_agent_id=dept_in.manager_agent_id,
    )
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@router.get("/{dept_id}", response_model=DepartmentResponse)
async def get_department(
    dept_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a department by ID."""
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
        )
    return dept


@router.get("/organizations/{org_id}", response_model=list[DepartmentResponse])
async def list_departments(
    org_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List departments for an organization."""
    result = await db.execute(
        select(Department).where(Department.organization_id == org_id)
    )
    return result.scalars().all()


# --- Teams ---

@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_in: TeamCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new team within a department."""
    team = Team(
        name=team_in.name,
        department_id=team_in.department_id,
        organization_id=team_in.organization_id,
    )
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


@router.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a team by ID."""
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )
    return team


# --- Department agent assignments ---

@router.post(
    "/assignments",
    response_model=DepartmentAgentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_agent_to_department(
    assignment_in: DepartmentAgentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Assign an agent to a department and/or team."""
    assignment = DepartmentAgent(
        agent_id=assignment_in.agent_id,
        department_id=assignment_in.department_id,
        team_id=assignment_in.team_id,
        role=assignment_in.role,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.get("/agents/{agent_id}/assignments", response_model=list[DepartmentAgentResponse])
async def list_agent_departments(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List department assignments for an agent."""
    result = await db.execute(
        select(DepartmentAgent).where(DepartmentAgent.agent_id == agent_id)
    )
    return result.scalars().all()
