"""Pydantic schemas for departments and teams."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# Department schemas
class DepartmentCreate(BaseModel):
    name: str
    organization_id: str
    manager_agent_id: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    manager_agent_id: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: UUID
    name: str
    organization_id: UUID
    manager_agent_id: Optional[UUID]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Team schemas
class TeamCreate(BaseModel):
    name: str
    department_id: str
    organization_id: str


class TeamResponse(BaseModel):
    id: UUID
    name: str
    department_id: UUID
    organization_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Department agent assignment schemas
class DepartmentAgentCreate(BaseModel):
    agent_id: str
    department_id: Optional[str] = None
    team_id: Optional[str] = None
    role: str = "specialist"


class DepartmentAgentResponse(BaseModel):
    id: UUID
    agent_id: UUID
    department_id: Optional[UUID]
    team_id: Optional[UUID]
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
