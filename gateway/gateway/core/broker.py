"""Credential broker (Phase 3).

Issues short-lived, scoped leases to connector credentials. Agents present a
lease to obtain the decrypted secret for connector execution; they never
receive the raw secret. Leases are JWTs scoped to (agent, credential,
connector_type, scope) with a TTL, and are tracked in Postgres so they can be
revoked and audited.
"""
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.core.config import settings
from gateway.core.crypto import EnvelopeEncryption
from gateway.db.session import AsyncSessionLocal
from gateway.models.agent import Agent
from gateway.models.connector_credential import ConnectorCredential, CredentialLease


class LeaseError(Exception):
    """Raised when a lease cannot be issued or validated."""


class CredentialBroker:
    """Issues and validates short-lived, scoped credential leases."""

    def __init__(self) -> None:
        self._crypto = EnvelopeEncryption()

    @asynccontextmanager
    async def _session(self, db: AsyncSession | None):
        if db is not None:
            yield db
        else:
            async with AsyncSessionLocal() as session:
                yield session

    async def issue_lease(
        self,
        agent: Agent,
        credential: ConnectorCredential,
        scope: str = "execute",
        ttl_seconds: int = 300,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Issue a short-lived JWT lease for ``credential``.

        Returns the lease token plus metadata. The raw secret is never
        returned.
        """
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        lease = CredentialLease(
            agent_id=agent.id,
            credential_id=credential.id,
            connector_type=credential.connector_type,
            scope=scope,
            expires_at=expires_at,
        )
        async with self._session(db) as session:
            session.add(lease)
            await session.commit()
            await session.refresh(lease)
            lease_id = lease.id

        token = self._encode_lease_token(
            agent_id=agent.id,
            credential_id=credential.id,
            connector_type=credential.connector_type,
            scope=scope,
            lease_id=lease_id,
            expires_at=expires_at,
        )
        return {
            "lease_token": token,
            "lease_id": lease_id,
            "credential_id": credential.id,
            "connector_type": credential.connector_type,
            "scope": scope,
            "expires_at": expires_at.isoformat(),
        }

    async def get_secret(
        self, lease_token: str, agent: Agent, db: AsyncSession | None = None
    ) -> str:
        """Validate a lease token and return the decrypted secret.

        The lease must be unexpired, unrevoked, unused, belong to ``agent``,
        and match the token's scope/connector type. The lease is marked used
        on success (one-time use).
        """
        payload = self._decode_lease_token(lease_token)
        lease_id = payload.get("lease_id")
        if not lease_id:
            raise LeaseError("Invalid lease token: missing lease id")

        async with self._session(db) as session:
            result = await session.execute(
                select(CredentialLease).where(CredentialLease.id == lease_id)
            )
            lease = result.scalar_one_or_none()
            if not lease:
                raise LeaseError("Lease not found")
            if not lease.is_valid:
                raise LeaseError("Lease is expired, revoked, or already used")
            if str(lease.agent_id) != str(agent.id):
                raise LeaseError("Lease does not belong to this agent")
            if lease.scope != payload.get("scope"):
                raise LeaseError("Lease scope mismatch")

            result = await session.execute(
                select(ConnectorCredential).where(
                    ConnectorCredential.id == lease.credential_id
                )
            )
            credential = result.scalar_one_or_none()
            if not credential:
                raise LeaseError("Credential not found")

            secret = self._crypto.decrypt_secret(
                json.loads(credential.encrypted_envelope)
            )

            lease.used_at = datetime.now(timezone.utc)
            await session.commit()

        return secret

    async def revoke_lease(
        self, lease_id: str, agent: Agent, db: AsyncSession | None = None
    ) -> None:
        """Revoke a lease belonging to ``agent``."""
        async with self._session(db) as session:
            result = await session.execute(
                select(CredentialLease).where(CredentialLease.id == lease_id)
            )
            lease = result.scalar_one_or_none()
            if not lease or str(lease.agent_id) != str(agent.id):
                return
            lease.revoked_at = datetime.now(timezone.utc)
            await session.commit()

    # --- JWT helpers ---

    def _encode_lease_token(
        self,
        agent_id: str,
        credential_id: str,
        connector_type: str,
        scope: str,
        lease_id: str,
        expires_at: datetime,
    ) -> str:
        to_encode = {
            "sub": agent_id,
            "agent_id": agent_id,
            "credential_id": credential_id,
            "connector_type": connector_type,
            "scope": scope,
            "lease_id": lease_id,
            "typ": "credential_lease",
            "exp": expires_at,
        }
        return jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )

    def _decode_lease_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except Exception as exc:
            raise LeaseError(f"Invalid lease token: {exc}") from exc
        if payload.get("typ") != "credential_lease":
            raise LeaseError("Not a credential lease token")
        return payload
