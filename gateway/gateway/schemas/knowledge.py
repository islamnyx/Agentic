"""Pydantic schemas for Company Brain knowledge items and access."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# Knowledge item schemas
class KnowledgeItemCreate(BaseModel):
    title: str
    content: Optional[str] = None
    category: str = "internal"
    department_id: Optional[str] = None
    organization_id: str
    is_confidential: bool = False


class KnowledgeItemUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    department_id: Optional[str] = None
    is_confidential: Optional[bool] = None


class KnowledgeItemResponse(BaseModel):
    id: UUID
    title: str
    content: Optional[str]
    category: str
    department_id: Optional[UUID]
    organization_id: UUID
    is_confidential: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Knowledge access (ACL) schemas
class KnowledgeAccessCreate(BaseModel):
    knowledge_item_id: str
    department_id: Optional[str] = None
    team_id: Optional[str] = None
    agent_id: Optional[str] = None
    permission: str = "read"
    granted_by: str


class KnowledgeAccessResponse(BaseModel):
    id: UUID
    knowledge_item_id: UUID
    department_id: Optional[UUID]
    team_id: Optional[UUID]
    agent_id: Optional[UUID]
    permission: str
    granted_by: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Knowledge access check (used by policy engine / security)
class KnowledgeAccessCheck(BaseModel):
    agent_id: UUID
    knowledge_item_id: UUID
    permission: str = "read"

    class Config:
        arbitrary_types_allowed = True

    def has_access(self, granted: bool) -> bool:
        return granted


# Knowledge ingestion pipeline (Phase 3)
class KnowledgeAccessGrantIn(BaseModel):
    department_id: Optional[str] = None
    team_id: Optional[str] = None
    agent_id: Optional[str] = None
    permission: str = "read"


class KnowledgeIngestRequest(BaseModel):
    title: str
    content: Optional[str] = None
    category: str = "internal"
    department_id: Optional[str] = None  # owning department
    organization_id: str
    is_confidential: bool = False
    access_grants: list[KnowledgeAccessGrantIn] = []  # ACL tags at ingest time


class KnowledgeIngestResponse(BaseModel):
    id: UUID
    title: str
    access_grants_created: int

    model_config = ConfigDict(from_attributes=True)
