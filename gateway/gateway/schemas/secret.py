"""Pydantic schemas for secrets and credential leases (Phase 3)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SecretCreate(BaseModel):
    name: str
    connector_type: str = Field(
        description="http, postgres, smtp, mcp, or playwright"
    )
    secret: str = Field(description="Plaintext secret value (never stored)")
    organization_id: str


class SecretResponse(BaseModel):
    id: UUID
    name: str
    connector_type: str
    key_id: Optional[str] = None
    kek_source: str
    organization_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SecretList(BaseModel):
    items: list[SecretResponse]


class LeaseRequest(BaseModel):
    credential_id: str
    scope: str = "execute"
    ttl_seconds: int = 300


class LeaseResponse(BaseModel):
    lease_token: str
    lease_id: str
    credential_id: str
    connector_type: str
    scope: str
    expires_at: datetime
