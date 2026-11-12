"""Tests for Phase 3 - Connectors.

Covers the envelope-encrypted secrets store, the credential broker (short-lived
scoped leases), the HTTP (SSRF + allowlist), PostgreSQL (read-only,
parameterized) and SMTP connectors, the MCP proxy (policy enforcement +
audit), and the invoke path where an agent does real work via a connector
without ever seeing a secret.
"""

import json
from datetime import timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from cryptography.exceptions import InvalidTag
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from gateway.api.deps import get_db
from gateway.connectors.base import ConnectorError
from gateway.connectors.http import HttpConnector, _is_private_ip
from gateway.connectors.postgres import (
    PostgresConnector,
    has_parameter_placeholders,
    is_read_only_select,
)
from gateway.connectors.smtp import SmtpConnector
from gateway.core.broker import CredentialBroker, LeaseError
from gateway.core.crypto import EnvelopeEncryption
from gateway.core.security import create_access_token
from gateway.db.session import Base
from gateway.main import app
from gateway.mcp.proxy import redact_pii
from gateway.models.agent import Agent
from gateway.models.connector_credential import ConnectorCredential
from gateway.models.knowledge_access import KnowledgeAccess
from gateway.models.knowledge_item import KnowledgeItem
from gateway.models.organization import Organization
from gateway.models.tool import Tool
from gateway.models.tool_call import ToolCall
from gateway.models.user import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_phase3.db"


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


async def _seed_org_user_agent(test_db, name="finance-agent", scopes="read_invoices"):
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
        name=name,
        scopes=scopes,
        organization_id=org.id,
        owner_id=user.id,
    )
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)
    return agent, org, user


async def _seed_credential(
    test_db, org_id, name="http-secret", connector_type="http", secret="top-secret"
):
    crypto = EnvelopeEncryption()
    envelope = crypto.encrypt_secret(secret)
    cred = ConnectorCredential(
        name=name,
        connector_type=connector_type,
        encrypted_envelope=__import__("json").dumps(envelope),
        key_id=envelope.get("key_id"),
        kek_source=envelope.get("kek_source", "local"),
        organization_id=org_id,
    )
    test_db.add(cred)
    await test_db.commit()
    await test_db.refresh(cred)
    return cred


async def _seed_mcp_tool(test_db, name="playwright", url="http://mcp.example.com"):
    tool = Tool(
        name=name,
        description="mcp server",
        connector_type="mcp",
        config=__import__("json").dumps({"url": url}),
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


class MockOpaResponse:
    def __init__(self, result, status_code=200):
        self._result = result
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            from httpx import HTTPStatusError
            raise HTTPStatusError("error", request=MagicMock(), response=self)

    def json(self):
        return {"result": self._result}


class MockOpaClient:
    def __init__(self, result, status_code=200):
        self._result = result
        self._status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None):
        return MockOpaResponse(self._result, self._status_code)


def opa_client(result, status_code=200):
    return patch(
        "gateway.core.opa.httpx.AsyncClient",
        return_value=MockOpaClient(result, status_code),
    )


# ---------------------------------------------------------------------------
# envelope encryption
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_envelope_encryption_roundtrip():
    crypto = EnvelopeEncryption()
    envelope = crypto.encrypt_secret("super-secret-value")
    assert set(envelope) == {
        "ciphertext",
        "nonce",
        "wrapped_dek",
        "key_id",
        "kek_source",
    }
    assert crypto.decrypt_secret(envelope) == "super-secret-value"
    # tampering fails
    envelope["ciphertext"] = "AAAA"
    with pytest.raises(InvalidTag):
        crypto.decrypt_secret(envelope)


# ---------------------------------------------------------------------------
# secrets API: metadata only, never plaintext
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_secret_stores_encrypted_not_plaintext(test_db):
    agent, org, user = await _seed_org_user_agent(test_db)
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/secrets/",
                headers={"Authorization": f"Bearer {_token(agent)}"},
                json={
                    "name": "db-password",
                    "connector_type": "postgres",
                    "secret": "the-real-password",
                    "organization_id": str(org.id),
                },
            )
            assert resp.status_code == 201, resp.text
            body = resp.json()
            assert body["name"] == "db-password"
            assert body["connector_type"] == "postgres"
            assert "secret" not in body  # plaintext never returned

            # list returns metadata only
            resp = await client.get(
                "/v1/secrets/",
                headers={"Authorization": f"Bearer {_token(agent)}"},
            )
            assert resp.status_code == 200
            items = resp.json()["items"]
            assert len(items) == 1
            assert "encrypted_envelope" not in items[0]
            assert "secret" not in items[0]

            # get single credential returns metadata only
            resp = await client.get(
                f"/v1/secrets/{body['id']}",
                headers={"Authorization": f"Bearer {_token(agent)}"},
            )
            assert resp.status_code == 200
            assert "secret" not in resp.json()
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_create_secret_cross_org_denied(test_db):
    agent, org, user = await _seed_org_user_agent(test_db)
    # a different org
    org2 = Organization(name="Other Org")
    test_db.add(org2)
    await test_db.commit()
    await test_db.refresh(org2)
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/secrets/",
                headers={"Authorization": f"Bearer {_token(agent)}"},
                json={
                    "name": "x",
                    "connector_type": "http",
                    "secret": "s",
                    "organization_id": str(org2.id),
                },
            )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# credential broker: short-lived scoped leases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broker_issue_and_get_secret(test_db):
    agent, org, user = await _seed_org_user_agent(test_db)
    cred = await _seed_credential(test_db, org.id)
    broker = CredentialBroker()
    lease = await broker.issue_lease(agent, cred, scope="execute", db=test_db)
    assert "lease_token" in lease
    assert "secret" not in lease  # token, not secret
    secret = await broker.get_secret(lease["lease_token"], agent, db=test_db)
    assert secret == "top-secret"


@pytest.mark.asyncio
async def test_broker_lease_one_time_use(test_db):
    agent, org, user = await _seed_org_user_agent(test_db)
    cred = await _seed_credential(test_db, org.id)
    broker = CredentialBroker()
    lease = await broker.issue_lease(agent, cred, db=test_db)
    await broker.get_secret(lease["lease_token"], agent, db=test_db)
    with pytest.raises(LeaseError):
        await broker.get_secret(lease["lease_token"], agent, db=test_db)


@pytest.mark.asyncio
async def test_broker_lease_scope_mismatch(test_db):
    agent, org, user = await _seed_org_user_agent(test_db)
    cred = await _seed_credential(test_db, org.id)
    broker = CredentialBroker()
    lease = await broker.issue_lease(agent, cred, scope="read", db=test_db)
    # tamper scope in token
    import jwt

    from gateway.core.config import settings
    token = jwt.encode(
        {
            "sub": agent.id,
            "agent_id": agent.id,
            "credential_id": cred.id,
            "connector_type": cred.connector_type,
            "scope": "execute",
            "lease_id": lease["lease_id"],
            "typ": "credential_lease",
            "exp": __import__("datetime").datetime.now(timezone.utc)
            + timedelta(minutes=30),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(LeaseError):
        await broker.get_secret(token, agent, db=test_db)


# ---------------------------------------------------------------------------
# HTTP connector: allowlist + SSRF
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_http_connector_allowlist_pass():
    conn = HttpConnector({"allowlist": ["example.com"]})
    conn.validate_params({"url": "https://example.com/api", "method": "GET"})


@pytest.mark.asyncio
async def test_http_connector_non_allowlisted_blocked():
    conn = HttpConnector({"allowlist": ["example.com"]})
    with pytest.raises(ConnectorError):
        conn.validate_params({"url": "https://evil.com/api"})


@pytest.mark.asyncio
async def test_http_connector_ssrf_private_ip_blocked():
    conn = HttpConnector({"allowlist": ["127.0.0.1"]})
    with pytest.raises(ConnectorError):
        conn.validate_params({"url": "http://127.0.0.1/metadata"})


@pytest.mark.asyncio
async def test_http_connector_ssrf_link_local_blocked():
    conn = HttpConnector({"allowlist": ["169.254.169.254"]})
    with pytest.raises(ConnectorError):
        conn.validate_params({"url": "http://169.254.169.254/"})


@pytest.mark.asyncio
async def test_http_connector_private_ip_helper():
    assert _is_private_ip("127.0.0.1") is True
    assert _is_private_ip("10.0.0.1") is True
    assert _is_private_ip("169.254.169.254") is True


@pytest.mark.asyncio
async def test_http_connector_invalid_scheme_blocked():
    conn = HttpConnector({"allowlist": ["example.com"]})
    with pytest.raises(ConnectorError):
        conn.validate_params({"url": "ftp://example.com/file"})


# ---------------------------------------------------------------------------
# PostgreSQL connector: read-only + parameterized
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_postgres_connector_read_only_enforced():
    conn = PostgresConnector({"host": "db", "dbname": "gateway"})
    with pytest.raises(ConnectorError):
        conn.validate_params(
            {"query": "UPDATE accounts SET balance = 0", "parameters": []}
        )
    with pytest.raises(ConnectorError):
        conn.validate_params(
            {"query": "SELECT * FROM accounts; DROP TABLE accounts", "parameters": []}
        )
    with pytest.raises(ConnectorError):
        conn.validate_params({"query": "DELETE FROM accounts", "parameters": []})


@pytest.mark.asyncio
async def test_postgres_connector_parameterized_required():
    conn = PostgresConnector()
    with pytest.raises(ConnectorError):
        conn.validate_params(
            {"query": "SELECT * FROM accounts WHERE id = 1", "parameters": []}
        )
    # parameterized SELECT passes validation
    conn.validate_params(
        {"query": "SELECT * FROM accounts WHERE id = $1", "parameters": [1]}
    )


def test_is_read_only_select():
    assert is_read_only_select("SELECT * FROM accounts") is True
    assert is_read_only_select("select id from users") is True
    assert is_read_only_select("UPDATE accounts SET x=1") is False
    assert is_read_only_select("SELECT * FROM t; DROP TABLE t") is False
    assert is_read_only_select("INSERT INTO t VALUES (1)") is False


def test_has_parameter_placeholders():
    assert has_parameter_placeholders("SELECT * FROM t WHERE id = $1") is True
    assert has_parameter_placeholders("SELECT * FROM t WHERE id = :id") is True
    assert has_parameter_placeholders("SELECT * FROM t WHERE id = ?") is True
    assert has_parameter_placeholders("SELECT * FROM t WHERE id = 1") is False


# ---------------------------------------------------------------------------
# SMTP connector validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_smtp_connector_validation():
    conn = SmtpConnector({"host": "smtp.example.com", "port": 587})
    with pytest.raises(ConnectorError):
        conn.validate_params({})
    conn.validate_params(
        {"to": "a@example.com", "subject": "hi", "body": "text"}
    )


# ---------------------------------------------------------------------------
# MCP proxy: policy enforcement + audit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_proxy_policy_denied(test_db):
    agent, org, user = await _seed_org_user_agent(test_db)
    await _seed_mcp_tool(test_db)
    denied = MagicMock()
    denied.decision = "denied"
    denied.deny = True
    denied.allow = False
    denied.require_approval = False
    denied.reasons = ["mcp calls not permitted"]
    with opa_client({"deny": True, "reasons": ["mcp calls not permitted"]}):
        from gateway.mcp.proxy import MCPProxy, McpProxyError

        proxy = MCPProxy()
        with pytest.raises(McpProxyError):
            await proxy.call(
                db=test_db,
                agent=agent,
                server_name="playwright",
                method="tools/call",
                params={"name": "navigate", "arguments": {"url": "http://x"}},
            )
    # audit recorded the denial
    result = await test_db.execute(select(ToolCall).where(ToolCall.agent_id == agent.id))
    call = result.scalars().first()
    assert call is not None
    assert call.decision == "denied"


# ---------------------------------------------------------------------------
# invoke via connector + lease: real work, agent never sees secret
# ---------------------------------------------------------------------------


class FakeConnector:
    connector_type = "http"

    async def execute(self, params, secret=None):
        assert secret == "injected-secret"  # secret injected, not from agent
        return {"status": 200, "body": {"fetched": True}}


@pytest.mark.asyncio
async def test_invoke_connector_executes_without_revealing_secret(test_db):
    agent, org, user = await _seed_org_user_agent(test_db, scopes="read_invoices")
    tool = Tool(
        name="fetch_invoices",
        description="http tool",
        connector_type="http",
        config=__import__("json").dumps({"allowlist": ["api.example.com"]}),
        is_active=True,
    )
    test_db.add(tool)
    await test_db.commit()
    await test_db.refresh(tool)

    cred = await _seed_credential(test_db, org.id, connector_type="http")
    broker = CredentialBroker()
    lease = await broker.issue_lease(agent, cred, scope="execute", db=test_db)

    allowed = MagicMock()
    allowed.decision = "allowed"
    allowed.allow = True
    allowed.deny = False
    allowed.require_approval = False
    allowed.reasons = ["connector invocation permitted"]

    app.dependency_overrides[get_db] = lambda: test_db
    try:
        with patch(
            "gateway.api.v1.tools.evaluate_policy", return_value=allowed
        ), patch(
            "gateway.api.v1.tools.CredentialBroker.get_secret",
            return_value="injected-secret",
        ), patch(
            "gateway.api.v1.tools.build_connector", return_value=FakeConnector()
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                resp = await client.post(
                    f"/v1/tools/{tool.name}/invoke",
                    headers={"Authorization": f"Bearer {_token(agent)}"},
                    json={
                        "parameters": {"url": "https://api.example.com/invoices"},
                        "lease_token": lease["lease_token"],
                    },
                )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["decision"] == "allowed"
        assert body["result"] == {"status": 200, "body": {"fetched": True}}

        # audit recorded the call
        result = await test_db.execute(
            select(ToolCall).where(ToolCall.agent_id == agent.id)
        )
        call = result.scalars().first()
        assert call is not None
        assert call.decision == "allowed"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_invoke_connector_without_lease_denied(test_db):
    agent, org, user = await _seed_org_user_agent(test_db)
    tool = Tool(
        name="fetch_invoices",
        connector_type="http",
        config=__import__("json").dumps({"allowlist": ["api.example.com"]}),
        is_active=True,
    )
    test_db.add(tool)
    await test_db.commit()
    await test_db.refresh(tool)
    allowed = MagicMock()
    allowed.decision = "allowed"
    allowed.allow = True
    allowed.deny = False
    allowed.require_approval = False
    allowed.reasons = ["ok"]
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        with patch(
            "gateway.api.v1.tools.evaluate_policy", return_value=allowed
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                resp = await client.post(
                    f"/v1/tools/{tool.name}/invoke",
                    headers={"Authorization": f"Bearer {_token(agent)}"},
                    json={"parameters": {"url": "https://api.example.com/x"}},
                )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Company Brain ingestion pipeline + ACL-enforced query
# ---------------------------------------------------------------------------


async def _seed_dept_team_assignment(test_db, org_id, agent_id):
    from gateway.models.department import Department
    from gateway.models.team import Team

    dept = Department(name="Finance", organization_id=org_id)
    test_db.add(dept)
    await test_db.commit()
    await test_db.refresh(dept)

    team = Team(
        name="Payments", department_id=dept.id, organization_id=org_id
    )
    test_db.add(team)
    await test_db.commit()
    await test_db.refresh(team)

    from gateway.models.department_agent import DepartmentAgent

    assignment = DepartmentAgent(
        agent_id=agent_id,
        department_id=dept.id,
        team_id=team.id,
        role="member",
    )
    test_db.add(assignment)
    await test_db.commit()
    await test_db.refresh(assignment)
    return dept, team


@pytest.mark.asyncio
async def test_ingest_knowledge_with_acl_tags(test_db):
    agent, org, user = await _seed_org_user_agent(test_db)
    await _seed_dept_team_assignment(test_db, org.id, agent.id)
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/knowledge/ingest",
                headers={"Authorization": f"Bearer {_token(agent)}"},
                json={
                    "title": "Pricing Guide",
                    "content": "Enterprise pricing details",
                    "category": "pricing",
                    "department_id": None,
                    "organization_id": str(org.id),
                    "is_confidential": True,
                    "access_grants": [
                        {
                            "department_id": None,
                            "team_id": None,
                            "agent_id": str(agent.id),
                            "permission": "read",
                        }
                    ],
                },
            )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["title"] == "Pricing Guide"
        assert body["access_grants_created"] == 1
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_ingest_knowledge_cross_org_denied(test_db):
    agent, org, user = await _seed_org_user_agent(test_db)
    org2 = Organization(name="Other Org")
    test_db.add(org2)
    await test_db.commit()
    await test_db.refresh(org2)
    app.dependency_overrides[get_db] = lambda: test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/knowledge/ingest",
                headers={"Authorization": f"Bearer {_token(agent)}"},
                json={
                    "title": "X",
                    "organization_id": str(org2.id),
                    "is_confidential": False,
                },
            )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_query_knowledge_acl_enforcement(test_db):
    agent, org, user = await _seed_org_user_agent(test_db)
    dept, team = await _seed_dept_team_assignment(test_db, org.id, agent.id)
    # another agent in same org without any grants
    agent2 = Agent(
        name="other-agent",
        organization_id=org.id,
        owner_id=user.id,
    )
    test_db.add(agent2)
    await test_db.commit()
    await test_db.refresh(agent2)

    # non-confidential item (org-wide readable)
    await _seed_knowledge_item(test_db, org.id, "Public Handbook", confidential=False)
    # confidential item with direct agent grant
    await _seed_knowledge_item(
        test_db, org.id, "Secret Payroll", confidential=True, agent_id=agent.id
    )
    # confidential item with department grant (agent is member of dept)
    await _seed_knowledge_item(
        test_db, org.id, "Dept Budget", confidential=True, department_id=dept.id
    )
    # confidential item with NO grant (should be hidden)
    await _seed_knowledge_item(test_db, org.id, "Hidden Vault", confidential=True)

    app.dependency_overrides[get_db] = lambda: test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            # agent sees public + payroll (direct grant) + budget (dept grant), not hidden
            resp = await client.get(
                "/v1/knowledge/query",
                headers={"Authorization": f"Bearer {_token(agent)}"},
            )
            assert resp.status_code == 200
            titles = {i["title"] for i in resp.json()}
            assert "Public Handbook" in titles
            assert "Secret Payroll" in titles
            assert "Dept Budget" in titles
            assert "Hidden Vault" not in titles

            # agent2 (no grants) sees only public handbook
            resp = await client.get(
                "/v1/knowledge/query",
                headers={"Authorization": f"Bearer {_token(agent2)}"},
            )
            assert resp.status_code == 200
            titles2 = {i["title"] for i in resp.json()}
            assert "Public Handbook" in titles2
            assert "Secret Payroll" not in titles2
            assert "Dept Budget" not in titles2
            assert "Hidden Vault" not in titles2
    finally:
        app.dependency_overrides.pop(get_db, None)


async def _seed_knowledge_item(
    test_db, org_id, title, confidential=False, agent_id=None, department_id=None
):
    item = KnowledgeItem(
        title=title,
        content="content for " + title,
        category="internal",
        department_id=department_id,
        organization_id=org_id,
        is_confidential=confidential,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    if confidential and (agent_id or department_id):
        access = KnowledgeAccess(
            knowledge_item_id=item.id,
            agent_id=agent_id,
            department_id=department_id,
            permission="read",
            granted_by="00000000-0000-0000-0000-000000000000",
        )
        test_db.add(access)
        await test_db.commit()
    return item


# ---------------------------------------------------------------------------
# PII redaction (MCP proxy hardening)
# ---------------------------------------------------------------------------


def test_redact_pii_masks_emails_phones_ssns_cards():
    payload = {
        "customer": "John Doe <john.doe@example.com>",
        "note": "call 555-123-4567 or +1-800-555-0199",
        "ids": {"ssn": "123-45-6789", "card": "4111-1111-1111-1111"},
        "nested": [{"email": "a@b.co", "raw": "no pii here"}],
        "number": 42,
    }
    redacted = redact_pii(payload)
    assert "john.doe@example.com" not in json.dumps(redacted)
    assert "555-123-4567" not in json.dumps(redacted)
    assert "+1-800-555-0199" not in json.dumps(redacted)
    assert "123-45-6789" not in json.dumps(redacted)
    assert "4111-1111-1111-1111" not in json.dumps(redacted)
    assert redacted["number"] == 42
    assert redacted["nested"][0]["raw"] == "no pii here"
    assert redacted["nested"][0]["email"] == "a***@b.co"
