"""Connector secrets and credential lease routes (Phase 3).

Connector credentials are stored envelope-encrypted (never plaintext). Listing
returns metadata only; the plaintext secret is never returned. Agents obtain
a short-lived, scoped lease to use a secret during connector execution.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.api.deps import get_current_agent, get_db
from gateway.core.broker import CredentialBroker, LeaseError
from gateway.core.crypto import EnvelopeEncryption
from gateway.models.connector_credential import ConnectorCredential
from gateway.models.organization import Organization
from gateway.schemas.secret import (
    LeaseRequest,
    LeaseResponse,
    SecretCreate,
    SecretList,
    SecretResponse,
)

router = APIRouter()

ALLOWED_CONNECTOR_TYPES = {
    "http",
    "postgres",
    "smtp",
    "mcp",
    "playwright",
}


@router.post(
    "/secrets/",
    response_model=SecretResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_secret(
    secret_in: SecretCreate,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Store an envelope-encrypted connector credential."""
    if secret_in.connector_type not in ALLOWED_CONNECTOR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported connector type: {secret_in.connector_type}",
        )
    result = await db.execute(
        select(Organization).where(Organization.id == secret_in.organization_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )
    if str(current_agent.organization_id) != secret_in.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Credential must belong to your organization",
        )

    envelope = EnvelopeEncryption().encrypt_secret(secret_in.secret)
    credential = ConnectorCredential(
        name=secret_in.name,
        connector_type=secret_in.connector_type,
        encrypted_envelope=json.dumps(envelope),
        key_id=envelope.get("key_id"),
        kek_source=envelope.get("kek_source", "local"),
        organization_id=secret_in.organization_id,
    )
    db.add(credential)
    await db.commit()
    await db.refresh(credential)
    return credential


@router.get("/secrets/", response_model=SecretList)
async def list_secrets(
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """List connector credential metadata (no plaintext secrets)."""
    result = await db.execute(
        select(ConnectorCredential).where(
            ConnectorCredential.organization_id == current_agent.organization_id
        )
    )
    return SecretList(items=result.scalars().all())


@router.get("/secrets/{credential_id}", response_model=SecretResponse)
async def get_secret(
    credential_id: str,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Get connector credential metadata (no plaintext secret)."""
    result = await db.execute(
        select(ConnectorCredential).where(ConnectorCredential.id == credential_id)
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found"
        )
    if str(credential.organization_id) != str(current_agent.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your organization's credential",
        )
    return credential


@router.delete("/secrets/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(
    credential_id: str,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Delete a connector credential."""
    result = await db.execute(
        select(ConnectorCredential).where(ConnectorCredential.id == credential_id)
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found"
        )
    if str(credential.organization_id) != str(current_agent.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your organization's credential",
        )
    await db.delete(credential)
    await db.commit()
    return None


@router.post(
    "/credentials/lease",
    response_model=LeaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_lease(
    lease_in: LeaseRequest,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Issue a short-lived, scoped lease to a connector credential.

    The response contains a lease token (JWT), never the raw secret. The
    token is presented when invoking a connector.
    """
    result = await db.execute(
        select(ConnectorCredential).where(
            ConnectorCredential.id == lease_in.credential_id
        )
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found"
        )
    if str(credential.organization_id) != str(current_agent.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your organization's credential",
        )

    broker = CredentialBroker()
    try:
        lease = await broker.issue_lease(
            current_agent, credential, scope=lease_in.scope,
            ttl_seconds=lease_in.ttl_seconds,
        )
    except LeaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return LeaseResponse(**lease)
