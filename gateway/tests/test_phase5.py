"""Tests for Phase 5 - Hash-chained audit log.

Covers:
* append creates a hash-chained entry
* verify passes on intact chain
* editing a DB row is detected by verification
* export to JSON
* Ed25519 signing of roots
"""

from datetime import timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from gateway.api.deps import get_db
from gateway.core.audit import AnchorService, AuditService
from gateway.core.observability import record_agent_cost, record_request
from gateway.core.security import create_access_token
from gateway.db.session import Base
from gateway.main import app
from gateway.models.agent import Agent
from gateway.models.audit_entry import AuditEntry
from gateway.models.metrics import AgentCost, DashboardMetric, SecurityIncident
from gateway.models.organization import Organization
from gateway.models.user import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_phase5.db"


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


async def _seed_agent(test_db):
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
        name="test-agent",
        scopes="read",
        organization_id=org.id,
        owner_id=user.id,
    )
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)
    return agent, org, user


def _token(agent):
    return create_access_token(
        data={"sub": agent.id, "agent_id": agent.id},
        expires_delta=timedelta(minutes=30),
    )


# ---------------------------------------------------------------------------
# Hash-chained audit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_append_creates_hash_chain(test_db):
    service = AuditService()
    e1 = await service.append(test_db, action="tool.invoke", actor_id="a1")
    e2 = await service.append(test_db, action="tool.invoke", actor_id="a1")
    assert e1.prev_hash == AuditEntry.genesis_hash()
    assert e2.prev_hash == e1.entry_hash
    assert e1.entry_hash != e2.entry_hash


@pytest.mark.asyncio
async def test_verify_intact_chain(test_db):
    service = AuditService()
    await service.append(test_db, action="a")
    await service.append(test_db, action="b")
    await service.append(test_db, action="c")
    ok, first_bad = await service.verify(test_db)
    assert ok is True
    assert first_bad is None


@pytest.mark.asyncio
async def test_verify_detects_tampering(test_db):
    """Editing a DB row is detected by verification."""
    service = AuditService()
    await service.append(test_db, action="a")
    await service.append(test_db, action="b")
    await service.append(test_db, action="c")

    # Tamper: modify the action of the second entry
    result = await test_db.execute(
        select(AuditEntry).where(AuditEntry.sequence == 2)
    )
    entry = result.scalar_one()
    entry.action = "tampered"
    await test_db.commit()

    ok, first_bad = await service.verify(test_db)
    assert ok is False
    assert first_bad == 2


@pytest.mark.asyncio
async def test_verify_detects_deletion(test_db):
    """Deleting a row breaks the chain."""
    service = AuditService()
    await service.append(test_db, action="a")
    await service.append(test_db, action="b")
    await service.append(test_db, action="c")

    # Delete the middle entry
    result = await test_db.execute(
        select(AuditEntry).where(AuditEntry.sequence == 2)
    )
    entry = result.scalar_one()
    await test_db.delete(entry)
    await test_db.commit()

    ok, first_bad = await service.verify(test_db)
    assert ok is False


@pytest.mark.asyncio
async def test_export_json(test_db):
    service = AuditService()
    await service.append(test_db, action="a", details={"x": 1})
    await service.append(test_db, action="b")
    entries = await service.export_json(test_db)
    assert len(entries) == 2
    assert entries[0]["action"] == "a"
    assert entries[0]["details"] == {"x": 1}
    assert "entry_hash" in entries[0]
    assert "prev_hash" in entries[0]


@pytest.mark.asyncio
async def test_sign_root_and_verify_signature(test_db):
    service = AuditService()
    await service.append(test_db, action="a")
    result = await service.sign_root(test_db)
    assert "signature" in result
    assert result["signature"] != ""
    assert service.verify_signature(result["signed_root"], result["signature"]) is True
    assert service.verify_signature(result["signed_root"], "0" * 128) is False


# ---------------------------------------------------------------------------
# Audit API endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_append_and_verify_api(test_db):
    agent, org, user = await _seed_agent(test_db)
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            token = _token(agent)
            resp = await client.post(
                "/v1/audit/append",
                headers={"Authorization": f"Bearer {token}"},
                json={"action": "tool.invoke", "details": {"tool": "x"}},
            )
            assert resp.status_code == 201, resp.text
            body = resp.json()
            assert "entry_hash" in body

            resp = await client.get(
                "/v1/audit/verify",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert resp.json()["ok"] is True

            resp = await client.get(
                "/v1/audit/export",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert resp.json()["count"] == 1
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# External hash anchoring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anchor_service_chain(tmp_path, monkeypatch):
    anchor_file = tmp_path / "anchors.log"
    monkeypatch.setenv("AUDIT_ANCHOR_PATH", str(anchor_file))
    anchor = AnchorService()
    r1 = anchor.anchor_root(
        audit_sequence=1, root_hash="root1", signature="sig1"
    )
    r2 = anchor.anchor_root(
        audit_sequence=2, root_hash="root2", signature="sig2"
    )
    assert r2["prev_anchor_hash"] == r1["anchor_hash"]
    ok, bad = anchor.verify_anchors()
    assert ok is True
    assert bad is None

    # Tamper: modify the first anchor's root_hash
    lines = anchor_file.read_text().splitlines()
    import json as _json

    obj = _json.loads(lines[0])
    obj["root_hash"] = "tampered-root"
    lines[0] = _json.dumps(obj, sort_keys=True, separators=(",", ":"))
    anchor_file.write_text("\n".join(lines) + "\n")

    ok, bad = anchor.verify_anchors()
    assert ok is False
    assert bad == 1


# ---------------------------------------------------------------------------
# Business metrics models
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_metric_model(test_db):
    m = DashboardMetric(
        metric_name="work_completed",
        metric_value=42.0,
        metric_unit="count",
        organization_id="org-1",
    )
    test_db.add(m)
    await test_db.commit()
    await test_db.refresh(m)
    assert m.id is not None
    assert m.metric_name == "work_completed"


@pytest.mark.asyncio
async def test_security_incident_model(test_db):
    inc = SecurityIncident(
        incident_type="audit_tampering",
        severity="high",
        description="row edited",
        actor_id="agent-1",
        actor_type="agent",
        organization_id="org-1",
    )
    test_db.add(inc)
    await test_db.commit()
    await test_db.refresh(inc)
    assert inc.resolved is False


@pytest.mark.asyncio
async def test_agent_cost_model(test_db):
    cost = AgentCost(
        agent_id="agent-1",
        organization_id="org-1",
        cost_type="mcp_call",
        amount=0.05,
        currency="USD",
    )
    test_db.add(cost)
    await test_db.commit()
    await test_db.refresh(cost)
    assert cost.amount == 0.05


# ---------------------------------------------------------------------------
# Observability helpers
# ---------------------------------------------------------------------------


def test_record_request_and_cost(monkeypatch):
    # Best-effort; should not raise even without an exporter configured.
    record_request(method="GET", path="/health", status_code=200)
    record_agent_cost(
        agent_id="agent-1", cost_type="tool_call", amount=1.25, currency="USD"
    )
    assert True


# ---------------------------------------------------------------------------
# Audit API: anchor-root endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_anchor_api(test_db, monkeypatch, tmp_path):
    anchor_file = tmp_path / "anchors.log"
    monkeypatch.setenv("AUDIT_ANCHOR_PATH", str(anchor_file))
    agent, org, user = await _seed_agent(test_db)
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            token = _token(agent)
            await client.post(
                "/v1/audit/append",
                headers={"Authorization": f"Bearer {token}"},
                json={"action": "tool.invoke"},
            )
            resp = await client.post(
                "/v1/audit/anchor-root",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["signed_root"] != ""
            assert body["signature"] != ""
            assert "anchor" in body
    finally:
        app.dependency_overrides.pop(get_db, None)

