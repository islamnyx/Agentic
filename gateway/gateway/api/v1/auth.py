"""Auth routes: login, token issuance, token revocation."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.api.deps import get_db
from gateway.core.security import create_access_token, hash_password
from gateway.models.agent import Agent
from gateway.models.agent_token import AgentToken
from gateway.schemas.agent import AgentLogin, TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def agent_login(
    login: AgentLogin,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate an agent and issue a short-lived JWT."""
    result = await db.execute(select(Agent).where(Agent.id == str(login.agent_id)))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if agent.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent is revoked",
        )

    # Revoke any existing active tokens for this agent (token rotation)
    result = await db.execute(
        select(AgentToken).where(
            AgentToken.agent_id == agent.id,
            AgentToken.revoked_at.is_(None),
        )
    )
    existing_tokens = result.scalars().all()
    now = datetime.now(timezone.utc)
    for t in existing_tokens:
        t.revoked_at = now

    # Create new JWT
    access_token = create_access_token(
        data={"sub": agent.id, "agent_id": agent.id},
        expires_delta=timedelta(minutes=30),
    )

    # Store token hash in DB
    token_hash = hash_password(access_token)
    new_token = AgentToken(
        id=str(uuid.uuid4()),
        agent_id=agent.id,
        token_hash=token_hash,
        expires_at=now + timedelta(minutes=30),
    )
    db.add(new_token)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=1800,
        agent_id=agent.id,
    )


@router.post("/revoke/{agent_id}")
async def revoke_agent_tokens(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Revoke all active tokens for an agent (emergency kill switch)."""
    result = await db.execute(select(Agent).where(Agent.id == str(agent_id)))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    agent.revoked_at = datetime.now(timezone.utc)

    result = await db.execute(
        select(AgentToken).where(
            AgentToken.agent_id == agent.id,
            AgentToken.revoked_at.is_(None),
        )
    )
    for t in result.scalars().all():
        t.revoked_at = datetime.now(timezone.utc)

    await db.commit()
    return {"status": "revoked", "agent_id": str(agent_id)}
