"""Agent registry routes: create, list, get agents."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.api.deps import get_db
from gateway.core.security import hash_password
from gateway.models.agent import Agent
from gateway.models.organization import Organization
from gateway.models.user import User
from gateway.schemas.agent import (
    AgentCreate,
    AgentResponse,
    OrganizationCreate,
    OrganizationResponse,
    UserCreate,
    UserResponse,
)

router = APIRouter()


# --- Organizations ---

@router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_in: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization."""
    org = Organization(name=org_in.name)
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get an organization by ID."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


# --- Users ---

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user."""
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = User(
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=user_in.role,
        organization_id=user_in.organization_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# --- Agents ---

@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_in: AgentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new agent."""
    agent = Agent(
        name=agent_in.name,
        scopes=agent_in.scopes,
        organization_id=agent_in.organization_id,
        owner_id=agent_in.owner_id,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/", response_model=list[AgentResponse])
async def list_agents(
    db: AsyncSession = Depends(get_db),
):
    """List all agents."""
    result = await db.execute(select(Agent))
    return result.scalars().all()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get an agent by ID."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent
