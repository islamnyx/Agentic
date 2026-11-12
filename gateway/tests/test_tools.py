"""Tests for tool registry and invoke (Phase 1)."""

import json
import uuid
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from gateway.core.config import settings
from gateway.core.security import create_access_token
from gateway.db.session import Base, get_db
from gateway.main import app
from gateway.models.agent import Agent
from gateway.models.organization import Organization
from gateway.models.tool import Tool
from gateway.models.tool_call import ToolCall
from gateway.models.user import User


TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_tools.db"


@pytest.fixture
async def test_db():
    """Create a test database session."""
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    test_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


async def _seed_agent(test_db: AsyncSession):
    org = Organization(name="Test Org")
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)

    user = User(
        email="owner@example.com",
        password_hash="hash",
        role="user",
        organization_id=org.id,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    agent = Agent(
        name="finance-agent",
        scopes="read_invoices,query_db",
        organization_id=org.id,
        owner_id=user.id,
    )
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)
    return agent


async def _seed_tools(test_db: AsyncSession):
    tools = [
        Tool(name="read_invoices", description="Read invoices", connector_type="native", is_active=True),
        Tool(name="query_db", description="Query database", connector_type="native", is_active=True),
        Tool(name="email_customers", description="Email customers", connector_type="smtp", is_active=False),
    ]
    test_db.add_all(tools)
    await test_db.commit()
    for t in tools:
        await test_db.refresh(t)
    return tools


@pytest.mark.asyncio
async def test_tool_registry_and_invoke(test_db: AsyncSession):
    """Agent registers, calls a mock tool, call recorded (Phase 1, dry-run policy)."""

    # Phase 2 policy engine: run in dry-run so OPA is not required for Phase 1 tests.
    previous_dry_run = settings.POLICY_DRY_RUN
    settings.POLICY_DRY_RUN = True
    # Phase 2 policy engine: run in dry-run so OPA is not required for Phase 1 tests.
    previous_dry_run = settings.POLICY_DRY_RUN
    settings.POLICY_DRY_RUN = True
    try:
        async def override_get_db():
            yield test_db

        app.dependency_overrides[get_db] = override_get_db
        try:
            agent = await _seed_agent(test_db)
            await _seed_tools(test_db)

            token = create_access_token(
                data={"sub": agent.id, "agent_id": agent.id},
                expires_delta=timedelta(minutes=30),
            )

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                headers = {"Authorization": f"Bearer {token}"}

                # List tools
                resp = await client.get("/v1/tools/", headers=headers)
                assert resp.status_code == 200
                names = [t["name"] for t in resp.json()]
                assert "read_invoices" in names
                assert "query_db" in names

                # Invoke a mock tool (dry-run: OPA decision logged but not enforced)
                resp = await client.post(
                    "/v1/tools/read_invoices/invoke",
                    headers=headers,
                    json={"parameters": {"org_id": "test", "limit": 10}},
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["decision"] == "allowed"
                assert "dry-run" in body["reason"]
                assert body["result"] is not None
                assert uuid.UUID(body["tool_call_id"])

                # Invoke an inactive tool -> 404
                resp = await client.post(
                    "/v1/tools/email_customers/invoke",
                    headers=headers,
                    json={"parameters": {"to": "a@b.com"}},
                )
                assert resp.status_code == 404

                # Invoke unknown tool -> 404
                resp = await client.post(
                    "/v1/tools/does_not_exist/invoke",
                    headers=headers,
                    json={"parameters": {}},
                )
                assert resp.status_code == 404

                # Unauthorized invoke -> 401
                resp = await client.post(
                    "/v1/tools/read_invoices/invoke",
                    json={"parameters": {}},
                )
                assert resp.status_code == 401

            # Verify the tool call was recorded
            result = await test_db.execute(
                select(ToolCall).where(ToolCall.agent_id == agent.id)
            )
            calls = result.scalars().all()
            assert len(calls) == 1
            call = calls[0]
            assert call.decision == "allowed"
            assert "dry-run" in call.decision_reason
            assert json.loads(call.parameters) == {"org_id": "test", "limit": 10}
            assert json.loads(call.result) is not None
        finally:
            app.dependency_overrides.pop(get_db, None)
    finally:
        settings.POLICY_DRY_RUN = previous_dry_run
