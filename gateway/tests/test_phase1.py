"""Tests for agent registry and identity (Phase 1)."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from gateway.core.security import create_access_token, hash_password, verify_password
from gateway.db.session import Base, AsyncSessionLocal, engine
from gateway.models.agent import Agent
from gateway.models.agent_token import AgentToken
from gateway.models.department import Department
from gateway.models.department_agent import DepartmentAgent
from gateway.models.knowledge_access import KnowledgeAccess
from gateway.models.knowledge_item import KnowledgeItem
from gateway.models.organization import Organization
from gateway.models.team import Team
from gateway.models.user import User


TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_gateway.db"


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


@pytest.mark.asyncio
async def test_hash_password():
    """Test password hashing and verification."""
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrong", hashed) is False


@pytest.mark.asyncio
async def test_create_and_decode_token():
    """Test JWT creation and decoding."""
    token = create_access_token(
        data={"sub": "agent-1", "agent_id": "agent-1"},
        expires_delta=timedelta(minutes=30),
    )
    assert isinstance(token, str)
    assert len(token) > 0

    payload = __import__("jwt").decode(token, "dev-secret-change-me", algorithms=["HS256"])
    assert payload["sub"] == "agent-1"
    assert payload["agent_id"] == "agent-1"
    assert "exp" in payload


@pytest.mark.asyncio
async def test_create_organization(test_db: AsyncSession):
    """Test creating an organization."""
    org = Organization(name="Test Org")
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)

    assert org.id is not None
    assert org.name == "Test Org"
    assert org.created_at is not None


@pytest.mark.asyncio
async def test_create_user(test_db: AsyncSession):
    """Test creating a user."""
    org = Organization(name="Test Org")
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)

    user = User(
        email="test@example.com",
        password_hash=hash_password("secret123"),
        role="user",
        organization_id=org.id,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert verify_password("secret123", user.password_hash) is True
    assert user.organization_id == org.id


@pytest.mark.asyncio
async def test_create_agent(test_db: AsyncSession):
    """Test creating/registration an agent."""
    org = Organization(name="Test Org")
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)

    user = User(
        email="owner@example.com",
        password_hash=hash_password("secret123"),
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

    assert agent.id is not None
    assert agent.name == "finance-agent"
    assert agent.is_revoked is False
    assert agent.scope_list == ["read_invoices", "query_db"]
    assert agent.organization_id == org.id
    assert agent.owner_id == user.id


@pytest.mark.asyncio
async def test_agent_revocation(test_db: AsyncSession):
    """Test agent revocation (kill switch)."""
    org = Organization(name="Test Org")
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)

    user = User(
        email="owner2@example.com",
        password_hash=hash_password("secret123"),
        organization_id=org.id,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    agent = Agent(
        name="revocable-agent",
        organization_id=org.id,
        owner_id=user.id,
    )
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)

    assert agent.is_revoked is False

    # Revoke
    agent.revoked_at = datetime.now(timezone.utc)
    await test_db.commit()

    assert agent.is_revoked is True


@pytest.mark.asyncio
async def test_token_expiry():
    """Test token expiry property."""
    token = AgentToken(
        id=str(uuid.uuid4()),
        agent_id="agent-1",
        token_hash="hash",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    assert token.is_expired is True

    token2 = AgentToken(
        id=str(uuid.uuid4()),
        agent_id="agent-1",
        token_hash="hash",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    assert token2.is_expired is False


@pytest.mark.asyncio
async def test_api_endpoints():
    """Test API endpoints with TestClient."""
    from fastapi.testclient import TestClient
    from gateway.main import app

    client = TestClient(app)

    # Test health
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Test root
    response = client.get("/v1/")
    assert response.status_code == 200
    assert response.json()["service"] == "gateway"


@pytest.mark.asyncio
async def test_create_department(test_db: AsyncSession):
    """Test creating a department."""
    org = Organization(name="Test Org")
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)

    dept = Department(name="Sales", organization_id=org.id)
    test_db.add(dept)
    await test_db.commit()
    await test_db.refresh(dept)

    assert dept.id is not None
    assert dept.name == "Sales"
    assert dept.organization_id == org.id
    assert dept.manager_agent_id is None


@pytest.mark.asyncio
async def test_create_team(test_db: AsyncSession):
    """Test creating a team within a department."""
    org = Organization(name="Test Org")
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)

    dept = Department(name="Sales", organization_id=org.id)
    test_db.add(dept)
    await test_db.commit()
    await test_db.refresh(dept)

    team = Team(name="Lead Research", department_id=dept.id, organization_id=org.id)
    test_db.add(team)
    await test_db.commit()
    await test_db.refresh(team)

    assert team.id is not None
    assert team.name == "Lead Research"
    assert team.department_id == dept.id
    assert team.organization_id == org.id


@pytest.mark.asyncio
async def test_assign_agent_to_department(test_db: AsyncSession):
    """Test assigning an agent to a department and team."""
    org = Organization(name="Test Org")
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)

    user = User(
        email="owner@example.com",
        password_hash=hash_password("secret123"),
        organization_id=org.id,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    agent = Agent(
        name="sales-agent",
        organization_id=org.id,
        owner_id=user.id,
    )
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)

    dept = Department(name="Sales", organization_id=org.id, manager_agent_id=agent.id)
    test_db.add(dept)
    await test_db.commit()
    await test_db.refresh(dept)

    team = Team(name="Lead Research", department_id=dept.id, organization_id=org.id)
    test_db.add(team)
    await test_db.commit()
    await test_db.refresh(team)

    assignment = DepartmentAgent(
        agent_id=agent.id,
        department_id=dept.id,
        team_id=team.id,
        role="manager",
    )
    test_db.add(assignment)
    await test_db.commit()
    await test_db.refresh(assignment)

    assert assignment.id is not None
    assert assignment.agent_id == agent.id
    assert assignment.department_id == dept.id
    assert assignment.team_id == team.id
    assert assignment.role == "manager"


@pytest.mark.asyncio
async def test_create_knowledge_item(test_db: AsyncSession):
    """Test creating a Company Brain knowledge item."""
    org = Organization(name="Test Org")
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)

    item = KnowledgeItem(
        title="Pricing Guide",
        content="Product pricing for enterprise plans",
        category="pricing",
        organization_id=org.id,
        is_confidential=True,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    assert item.id is not None
    assert item.title == "Pricing Guide"
    assert item.category == "pricing"
    assert item.is_confidential is True
    assert item.organization_id == org.id


@pytest.mark.asyncio
async def test_grant_knowledge_access(test_db: AsyncSession):
    """Test granting per-item knowledge access (ACL)."""
    org = Organization(name="Test Org")
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)

    user = User(
        email="admin@example.com",
        password_hash=hash_password("secret123"),
        organization_id=org.id,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    item = KnowledgeItem(
        title="HR Handbook",
        content="Confidential HR policies",
        category="internal",
        organization_id=org.id,
        is_confidential=True,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    access = KnowledgeAccess(
        knowledge_item_id=item.id,
        agent_id=None,
        department_id=None,
        permission="read",
        granted_by=user.id,
    )
    test_db.add(access)
    await test_db.commit()
    await test_db.refresh(access)

    assert access.id is not None
    assert access.knowledge_item_id == item.id
    assert access.permission == "read"
    assert access.granted_by == user.id


@pytest.mark.asyncio
async def test_department_and_knowledge_api_endpoints(test_db: AsyncSession):
    """Test department and knowledge API endpoints with AsyncClient + DB override."""
    from httpx import ASGITransport, AsyncClient

    from gateway.api.deps import get_db
    from gateway.main import app
    from gateway.models.organization import Organization

    # Seed an organization directly via the model
    org = Organization(name="Test Org")
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)
    org_id = str(org.id)

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            # Create department
            response = await client.post(
                "/v1/departments/",
                json={"name": "Sales", "organization_id": org_id},
            )
            assert response.status_code == 201
            assert response.json()["name"] == "Sales"

            # List departments for org
            response = await client.get(f"/v1/departments/organizations/{org_id}")
            assert response.status_code == 200
            assert len(response.json()) == 1

            # Create knowledge item
            response = await client.post(
                "/v1/knowledge/",
                json={
                    "title": "Pricing Guide",
                    "category": "pricing",
                    "organization_id": org_id,
                    "is_confidential": True,
                },
            )
            assert response.status_code == 201
            item_id = response.json()["id"]
            assert response.json()["title"] == "Pricing Guide"

            # List knowledge items for org
            response = await client.get(f"/v1/knowledge/organizations/{org_id}")
            assert response.status_code == 200
            assert len(response.json()) == 1

            # Grant knowledge access
            response = await client.post(
                "/v1/knowledge/access",
                json={
                    "knowledge_item_id": item_id,
                    "permission": "read",
                    "granted_by": org_id,  # stand-in user id for the test
                },
            )
            assert response.status_code == 201
            assert response.json()["permission"] == "read"

            # List knowledge access
            response = await client.get(f"/v1/knowledge/{item_id}/access")
            assert response.status_code == 200
            assert len(response.json()) == 1
    finally:
        app.dependency_overrides.pop(get_db, None)
