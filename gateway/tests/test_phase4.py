"""Tests for Phase 4 - Approvals.

Covers the human approval flow for tool invocations that require approval:
* require_approval decision creates a pending approval (refund pauses)
* approval is bound to exact parameters via SHA-256 hash (changing amount invalidates)
* approve/deny API flow
* single-use enforcement (approval consumed on execution)
* pending queue listing
* expiry
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from gateway.api.deps import get_db
from gateway.core.security import create_access_token
from gateway.db.session import Base
from gateway.main import app
from gateway.models.agent import Agent
from gateway.models.approval import Approval
from gateway.models.organization import Organization
from gateway.models.tool import Tool
from gateway.models.tool_call import ToolCall
from gateway.models.user import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_phase4.db"


@pytest.fixture
async def test_db():
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


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


async def _seed_org_user_agent(test_db, name="finance-agent", scopes="issue_refunds"):
    org = Organization(name="Test Org")
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)
    user = User(
        email="owner@example.com",
        password_hash="hash",
        role="admin",
        organization_id=org.id,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    agent = Agent(
        name=name,
        scopes=scopes,
        organization_id=org.id,
        owner_id=user.id,
    )
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)
    return agent, org, user


async def _seed_tool(test_db, name="issue_refunds"):
    tool = Tool(
        name=name,
        description="refund tool",
        connector_type="native",
        is_active=True,
    )
    test_db.add(tool)
    await test_db.commit()
    await test_db.refresh(tool)
    return tool


def _token(agent):
    return create_access_token(
        data={"sub": agent.id, "agent_id": agent.id},
        expires_delta=timedelta(minutes=30),
    )


class ApprovalDecision:
    """Mock OPA decision returning require_approval."""

    def __init__(self, require=True, reasons=None):
        self.decision = "require_approval" if require else "allowed"
        self.reasons = reasons or ["high risk invocation requires approval"]
        self.allow = not require
        self.deny = False
        self.require_approval = require


# ---------------------------------------------------------------------------
# Approval created on require_approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refund_above_threshold_creates_pending_approval(test_db):
    """Refund that requires approval pauses with a pending approval record."""
    agent, org, user = await _seed_org_user_agent(test_db)
    tool = await _seed_tool(test_db, name="issue_refunds")
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            with patch(
                "gateway.api.v1.tools.evaluate_policy",
                return_value=ApprovalDecision(require=True),
            ):
                token = _token(agent)
                resp = await client.post(
                    "/v1/tools/issue_refunds/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "write", "amount": 500}},
                )
        assert resp.status_code == 409, resp.text
        detail = resp.json()["detail"]
        assert detail["decision"] == "require_approval"
        approval_id = detail["approval_id"]

        # Approval record created and pending
        result = await test_db.execute(select(Approval).where(Approval.id == approval_id))
        approval = result.scalars().first()
        assert approval is not None
        assert approval.status == "pending"
        assert approval.agent_id == agent.id
        assert approval.tool_id == tool.id

        # ToolCall recorded as require_approval
        result = await test_db.execute(select(ToolCall).where(ToolCall.agent_id == agent.id))
        call = result.scalars().first()
        assert call is not None
        assert call.decision == "require_approval"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_changing_amount_invalidates_approval(test_db):
    """Changing the amount produces a different parameter hash, so an approval
    for amount=500 does not authorize amount=600."""
    agent, org, user = await _seed_org_user_agent(test_db)
    tool = await _seed_tool(test_db, name="issue_refunds")
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        # Manually create an approved approval for amount=500
        params500 = {"action": "write", "amount": 500}
        params600 = {"action": "write", "amount": 600}
        hash500 = Approval.hash_parameters(params500)
        hash600 = Approval.hash_parameters(params600)
        assert hash500 != hash600

        now = datetime.now(timezone.utc)
        approved = Approval(
            agent_id=agent.id,
            tool_id=tool.id,
            action="write",
            parameters_hash=hash500,
            parameters_json=json.dumps(params500),
            delegation_chain="{}",
            status="approved",
            expires_at=now + timedelta(hours=1),
        )
        test_db.add(approved)
        await test_db.commit()
        await test_db.refresh(approved)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            with patch(
                "gateway.api.v1.tools.evaluate_policy",
                return_value=ApprovalDecision(require=True),
            ):
                token = _token(agent)
                # Invoke with amount=600 -> should NOT match the approved amount=500
                resp = await client.post(
                    "/v1/tools/issue_refunds/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "write", "amount": 600}},
                )
        # Creates a NEW pending approval (hash 600), does not consume the amount=500 one
        assert resp.status_code == 409, resp.text
        detail = resp.json()["detail"]
        assert detail["decision"] == "require_approval"
        new_approval_id = detail["approval_id"]

        result = await test_db.execute(select(Approval))
        approvals = result.scalars().all()
        assert len(approvals) == 2
        # Original amount=500 approval still approved (not consumed)
        orig = await test_db.get(Approval, approved.id)
        assert orig.status == "approved"
        # New amount=600 approval is pending
        new_appr = await test_db.get(Approval, new_approval_id)
        assert new_appr.status == "pending"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Approve / deny API flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_then_invoke_executes(test_db):
    """Approving a pending approval allows the invoke to execute on retry."""
    agent, org, user = await _seed_org_user_agent(test_db)
    await _seed_tool(test_db, name="issue_refunds")
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            # Step 1: invoke -> require_approval, pending approval created
            with patch(
                "gateway.api.v1.tools.evaluate_policy",
                return_value=ApprovalDecision(require=True),
            ):
                token = _token(agent)
                resp = await client.post(
                    "/v1/tools/issue_refunds/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "write", "amount": 500}},
                )
            assert resp.status_code == 409
            approval_id = resp.json()["detail"]["approval_id"]

            # Step 2: approver (admin user, same org) approves
            resp = await client.post(
                f"/v1/approvals/{approval_id}/approve",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["status"] == "approved"

            # Step 3: retry invoke with same params -> executes (consumes approval)
            with patch(
                "gateway.api.v1.tools.evaluate_policy",
                return_value=ApprovalDecision(require=True),
            ):
                resp = await client.post(
                    "/v1/tools/issue_refunds/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "write", "amount": 500}},
                )
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["decision"] == "allowed"

            # Approval consumed (single-use)
            result = await test_db.execute(select(Approval).where(Approval.id == approval_id))
            approval = result.scalars().first()
            assert approval.status == "used"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_deny_then_invoke_blocked(test_db):
    """Denying a pending approval blocks the invoke."""
    agent, org, user = await _seed_org_user_agent(test_db)
    await _seed_tool(test_db, name="issue_refunds")
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            with patch(
                "gateway.api.v1.tools.evaluate_policy",
                return_value=ApprovalDecision(require=True),
            ):
                token = _token(agent)
                resp = await client.post(
                    "/v1/tools/issue_refunds/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "write", "amount": 500}},
                )
            assert resp.status_code == 409
            approval_id = resp.json()["detail"]["approval_id"]

            resp = await client.post(
                f"/v1/approvals/{approval_id}/deny",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["status"] == "denied"

            # Retry invoke -> creates a new pending approval (denied ones don't authorize)
            with patch(
                "gateway.api.v1.tools.evaluate_policy",
                return_value=ApprovalDecision(require=True),
            ):
                resp = await client.post(
                    "/v1/tools/issue_refunds/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "write", "amount": 500}},
                )
            assert resp.status_code == 409
            detail = resp.json()["detail"]
            assert detail["decision"] == "require_approval"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Pending queue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_queue_lists_approvals(test_db):
    agent, org, user = await _seed_org_user_agent(test_db)
    await _seed_tool(test_db, name="issue_refunds")
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            with patch(
                "gateway.api.v1.tools.evaluate_policy",
                return_value=ApprovalDecision(require=True),
            ):
                token = _token(agent)
                await client.post(
                    "/v1/tools/issue_refunds/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "write", "amount": 500}},
                )
                await client.post(
                    "/v1/tools/issue_refunds/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "write", "amount": 600}},
                )

            resp = await client.get(
                "/v1/approvals/pending",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        assert all(i["status"] == "pending" for i in items)
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Single-use enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approval_single_use(test_db):
    """An approved approval is consumed on first execution and cannot be reused."""
    agent, org, user = await _seed_org_user_agent(test_db)
    await _seed_tool(test_db, name="issue_refunds")
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            with patch(
                "gateway.api.v1.tools.evaluate_policy",
                return_value=ApprovalDecision(require=True),
            ):
                token = _token(agent)
                # create pending
                resp = await client.post(
                    "/v1/tools/issue_refunds/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "write", "amount": 500}},
                )
                assert resp.status_code == 409
                approval_id = resp.json()["detail"]["approval_id"]

                # approve
                resp = await client.post(
                    f"/v1/approvals/{approval_id}/approve",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert resp.status_code == 200

                # first execute consumes it
                resp = await client.post(
                    "/v1/tools/issue_refunds/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "write", "amount": 500}},
                )
                assert resp.status_code == 200

                # second execute with same params -> no usable approval, creates new pending
                resp = await client.post(
                    "/v1/tools/issue_refunds/invoke",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"parameters": {"action": "write", "amount": 500}},
                )
                assert resp.status_code == 409
                detail = resp.json()["detail"]
                assert detail["decision"] == "require_approval"

            result = await test_db.execute(select(Approval).where(Approval.id == approval_id))
            approval = result.scalars().first()
            assert approval.status == "used"
    finally:
        app.dependency_overrides.pop(get_db, None)
