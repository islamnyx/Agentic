"""Tests for Phase 2 - Policy Engine.

Covers OPA policy evaluation (allow / deny / require_approval), department-scoped
and knowledge ACL policies, and the invoke endpoint logging decisions + deny
reasons to the ToolCall record.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from gateway.core.config import settings
from gateway.core.opa import PolicyDecision
from gateway.core.security import create_access_token
from gateway.db.session import Base, get_db
from gateway.main import app
from gateway.models.agent import Agent
from gateway.models.organization import Organization
from gateway.models.tool import Tool
from gateway.models.tool_call import ToolCall
from gateway.models.user import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_phase2.db"


@pytest.fixture
async def test_db():
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    test_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


class MockOpaResponse:
    """Mock httpx.Response returning a canned OPA decision payload."""

    def __init__(self, result: dict, status_code: int = 200):
        self._result = result
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            from httpx import HTTPStatusError

            raise HTTPStatusError("error", request=MagicMock(), response=self)

    def json(self):
        return {"result": self._result}


class MockOpaClient:
    """Mock httpx.AsyncClient used by gateway.core.opa.evaluate_policy."""

    def __init__(self, result: dict, status_code: int = 200):
        self._result = result
        self._status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None):
        return MockOpaResponse(self._result, self._status_code)


@pytest.fixture
def opa_result():
    return {"allow": False, "deny": False, "require_approval": False, "reasons": []}


def opa_client(result, status_code=200):
    return patch(
        "gateway.core.opa.httpx.AsyncClient",
        return_value=MockOpaClient(result, status_code),
    )


async def _seed_agent(test_db: AsyncSession, scopes: str = "read_invoices,query_db"):
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
        scopes=scopes,
        organization_id=org.id,
        owner_id=user.id,
    )
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)
    return agent, org, user


async def _seed_tool(test_db: AsyncSession, name: str = "read_invoices"):
    tool = Tool(name=name, description="desc", connector_type="native", is_active=True)
    test_db.add(tool)
    await test_db.commit()
    await test_db.refresh(tool)
    return tool


# ---------------------------------------------------------------------------
# OPA policy decision evaluation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_policy_allowed(opa_result):
    """Scoped low-risk invocation is allowed."""
    opa_result.update(
        allow=True, deny=False, require_approval=False,
        decision="allowed", reasons=["tool invocation permitted by policy"],
    )
    with opa_client(opa_result):
        from gateway.core.opa import evaluate_policy

        decision = await evaluate_policy(
            {
                "who": {
                    "agent": {"id": "a-1", "name": "finance-agent", "scopes": ["read_invoices"]},
                    "owner": {"id": "u-1", "role": "user"},
                    "org": {"id": "org-1"},
                },
                "what": {"tool": "read_invoices", "action": "read", "parameters": {}},
                "on_what": {"resource_type": None, "resource_id": None, "tenant_id": None},
                "context": {
                    "session_id": "s-1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "risk_level": "low",
                    "data_labels": ["internal"],
                },
            }
        )
    assert decision.decision == "allowed"
    assert decision.allow is True
    assert decision.deny is False


@pytest.mark.asyncio
async def test_evaluate_policy_denied_no_scope(opa_result):
    """Invocation without a matching scope is denied with a reason."""
    opa_result.update(
        allow=False, deny=True, require_approval=False,
        decision="denied", reasons=["no matching scope for tool issue_refunds"],
    )
    with opa_client(opa_result):
        from gateway.core.opa import evaluate_policy

        decision = await evaluate_policy(
            {
                "who": {
                    "agent": {"id": "a-1", "name": "finance-agent", "scopes": ["read_invoices"]},
                    "owner": {"id": "u-1", "role": "user"},
                    "org": {"id": "org-1"},
                },
                "what": {"tool": "issue_refunds", "action": "write", "parameters": {}},
                "on_what": {"resource_type": None, "resource_id": None, "tenant_id": None},
                "context": {
                    "session_id": "s-1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "risk_level": "medium",
                    "data_labels": ["internal"],
                },
            }
        )
    assert decision.decision == "denied"
    assert decision.deny is True
    assert decision.reasons


@pytest.mark.asyncio
async def test_evaluate_policy_denied_critical_risk(opa_result):
    """Critical risk invocations are denied even when scoped."""
    opa_result.update(
        allow=False, deny=True, require_approval=False,
        decision="denied", reasons=["critical risk invocations are denied"],
    )
    with opa_client(opa_result):
        from gateway.core.opa import evaluate_policy

        decision = await evaluate_policy(
            {
                "who": {
                    "agent": {"id": "a-1", "name": "finance-agent", "scopes": ["issue_refunds"]},
                    "owner": {"id": "u-1", "role": "user"},
                    "org": {"id": "org-1"},
                },
                "what": {"tool": "issue_refunds", "action": "write", "parameters": {}},
                "on_what": {"resource_type": None, "resource_id": None, "tenant_id": None},
                "context": {
                    "session_id": "s-1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "risk_level": "critical",
                    "data_labels": ["internal"],
                },
            }
        )
    assert decision.decision == "denied"
    assert any("critical" in r.lower() for r in decision.reasons)


@pytest.mark.asyncio
async def test_evaluate_policy_require_approval_high_risk(opa_result):
    """High-risk scoped invocations require approval."""
    opa_result.update(
        allow=False, deny=False, require_approval=True,
        decision="require_approval", reasons=["high risk invocation requires approval"],
    )
    with opa_client(opa_result):
        from gateway.core.opa import evaluate_policy

        decision = await evaluate_policy(
            {
                "who": {
                    "agent": {"id": "a-1", "name": "finance-agent", "scopes": ["issue_refunds"]},
                    "owner": {"id": "u-1", "role": "user"},
                    "org": {"id": "org-1"},
                },
                "what": {"tool": "issue_refunds", "action": "write", "parameters": {"amount": 500}},
                "on_what": {"resource_type": None, "resource_id": None, "tenant_id": None},
                "context": {
                    "session_id": "s-1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "risk_level": "high",
                    "data_labels": ["internal"],
                },
            }
        )
    assert decision.decision == "require_approval"
    assert decision.require_approval is True


@pytest.mark.asyncio
async def test_evaluate_policy_cross_department_denied(opa_result):
    """Cross-organization high-risk calls are denied/require approval."""
    opa_result.update(
        allow=False, deny=True, require_approval=False,
        decision="denied", reasons=["cross-department high-risk call denied"],
    )
    with opa_client(opa_result):
        from gateway.core.opa import evaluate_policy

        decision = await evaluate_policy(
            {
                "who": {
                    "agent": {"id": "a-1", "name": "finance-agent", "scopes": ["read_invoices"]},
                    "owner": {"id": "u-1", "role": "user"},
                    "org": {"id": "org-1"},
                },
                "what": {"tool": "read_invoices", "action": "read", "parameters": {}},
                "on_what": {
                    "resource_type": None,
                    "resource_id": None,
                    "tenant_id": "org-2",
                },
                "context": {
                    "session_id": "s-1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "risk_level": "high",
                    "data_labels": ["internal"],
                },
            }
        )
    assert decision.decision in ("denied", "require_approval")


@pytest.mark.asyncio
async def test_evaluate_policy_knowledge_acl_denied(opa_result):
    """Reading a confidential knowledge item without ACL grant is denied."""
    opa_result.update(
        allow=False, deny=True, require_approval=False,
        decision="denied", reasons=["knowledge item read not permitted by ACL"],
    )
    with opa_client(opa_result):
        from gateway.core.opa import evaluate_policy

        decision = await evaluate_policy(
            {
                "who": {
                    "agent": {"id": "a-1", "name": "sales-agent", "scopes": ["query_knowledge"]},
                    "owner": {"id": "u-1", "role": "user"},
                    "org": {"id": "org-1"},
                },
                "what": {
                    "tool": "query_knowledge",
                    "action": "read",
                    "parameters": {"category": "hr"},
                },
                "on_what": {
                    "resource_type": "knowledge_item",
                    "resource_id": "ki-1",
                    "tenant_id": None,
                },
                "context": {
                    "session_id": "s-1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "risk_level": "medium",
                    "data_labels": ["internal"],
                },
            }
        )
    assert decision.decision == "denied"
    assert any("knowledge" in r.lower() or "ACL" in r for r in decision.reasons)


@pytest.mark.asyncio
async def test_evaluate_policy_opa_unreachable_fail_closed():
    """OPA unreachable => fail-closed deny (unless dry-run)."""
    settings.POLICY_DRY_RUN = False
    try:
        with patch(
            "gateway.core.opa.httpx.AsyncClient",
            side_effect=Exception("connection refused"),
        ):
            from gateway.core.opa import evaluate_policy

            decision = await evaluate_policy(
                {
                    "who": {"agent": {"id": "a-1", "scopes": ["read_invoices"]}},
                    "what": {"tool": "read_invoices", "action": "read", "parameters": {}},
                    "on_what": {},
                    "context": {"risk_level": "low", "data_labels": ["internal"]},
                }
            )
        assert decision.decision == "denied"
    finally:
        settings.POLICY_DRY_RUN = False


# ---------------------------------------------------------------------------
# Invoke endpoint: decisions logged with reasons
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invoke_allowed_logs_decision(test_db: AsyncSession):
    """Allowed invoke is recorded with decision=allowed and policy reason."""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        agent, org, user = await _seed_agent(test_db)
        await _seed_tool(test_db, name="read_invoices")
        allowed = PolicyDecision(
            decision="allowed",
            reasons=["tool invocation permitted by policy"],
            allow=True,
            deny=False,
            require_approval=False,
        )
        with patch(
            "gateway.api.v1.tools.evaluate_policy", return_value=allowed
        ):
            token = create_access_token(
                data={"sub": agent.id, "agent_id": agent.id},
                expires_delta=timedelta(minutes=30),
            )
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                resp = await client.post(
                    "/v1/tools/read_invoices/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "read"}},
                )
            assert resp.status_code == 200
            body = resp.json()
            assert body["decision"] == "allowed"
            assert "policy" in body["reason"]

        result = await test_db.execute(
            select(ToolCall).where(ToolCall.agent_id == agent.id)
        )
        call = result.scalars().first()
        assert call is not None
        assert call.decision == "allowed"
        assert call.decision_reason is not None
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_invoke_denied_logs_reason(test_db: AsyncSession):
    """Denied invoke returns 403 and records decision=denied with deny reason."""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        agent, org, user = await _seed_agent(test_db)
        await _seed_tool(test_db, name="issue_refunds")
        denied = PolicyDecision(
            decision="denied",
            reasons=["no matching scope for tool issue_refunds"],
            allow=False,
            deny=True,
            require_approval=False,
        )
        with patch(
            "gateway.api.v1.tools.evaluate_policy", return_value=denied
        ):
            token = create_access_token(
                data={"sub": agent.id, "agent_id": agent.id},
                expires_delta=timedelta(minutes=30),
            )
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                resp = await client.post(
                    "/v1/tools/issue_refunds/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "write", "amount": 500}},
                )
            assert resp.status_code == 403
            detail = resp.json()["detail"]
            assert detail["decision"] == "denied"
            assert detail["reasons"]

        result = await test_db.execute(
            select(ToolCall).where(ToolCall.agent_id == agent.id)
        )
        call = result.scalars().first()
        assert call is not None
        assert call.decision == "denied"
        assert "scope" in call.decision_reason
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_invoke_require_approval(test_db: AsyncSession):
    """Require-approval invoke returns 409 and records decision=require_approval."""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        agent, org, user = await _seed_agent(test_db)
        await _seed_tool(test_db, name="issue_refunds")
        approval = PolicyDecision(
            decision="require_approval",
            reasons=["high risk invocation requires approval"],
            allow=False,
            deny=False,
            require_approval=True,
        )
        with patch(
            "gateway.api.v1.tools.evaluate_policy", return_value=approval
        ):
            token = create_access_token(
                data={"sub": agent.id, "agent_id": agent.id},
                expires_delta=timedelta(minutes=30),
            )
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                resp = await client.post(
                    "/v1/tools/issue_refunds/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "write", "amount": 500}},
                )
            assert resp.status_code == 409
            detail = resp.json()["detail"]
            assert detail["decision"] == "require_approval"

        result = await test_db.execute(
            select(ToolCall).where(ToolCall.agent_id == agent.id)
        )
        call = result.scalars().first()
        assert call is not None
        assert call.decision == "require_approval"
    finally:
        app.dependency_overrides.pop(get_db, None)

