"""API dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.db.session import AsyncSessionLocal, get_db
from gateway.core.security import decode_token
from gateway.models.agent import Agent
from sqlalchemy import select

security = HTTPBearer()


async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_agent(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """Validate JWT and return the current agent."""
    try:
        payload = decode_token(credentials.credentials)
        agent_id = payload.get("agent_id")
        if not agent_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
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
    return agent
