"""Pydantic schemas for agents and auth."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


# Organization schemas
class OrganizationCreate(BaseModel):
    name: str


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "user"
    organization_id: Optional[UUID] = None


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    organization_id: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True


# Agent schemas
class AgentCreate(BaseModel):
    name: str
    organization_id: UUID
    owner_id: UUID
    scopes: str = ""


class AgentResponse(BaseModel):
    id: UUID
    name: str
    scopes: str
    revoked_at: Optional[datetime]
    organization_id: UUID
    owner_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Token schemas
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    agent_id: UUID


class AgentLogin(BaseModel):
    agent_id: UUID
