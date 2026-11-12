"""Company Brain knowledge item and access routes.

Provides CRUD for knowledge items and per-item access control lists (ACLs).
Access permissions apply to the knowledge itself — enforced outside the LLM.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.api.deps import get_current_agent, get_db
from gateway.models.department_agent import DepartmentAgent
from gateway.models.knowledge_access import KnowledgeAccess
from gateway.models.knowledge_item import KnowledgeItem
from gateway.schemas.knowledge import (
    KnowledgeAccessCreate,
    KnowledgeAccessResponse,
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
    KnowledgeItemCreate,
    KnowledgeItemResponse,
    KnowledgeItemUpdate,
)

router = APIRouter()


# --- Knowledge items ---

@router.post("/", response_model=KnowledgeItemResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_item(
    item_in: KnowledgeItemCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a Company Brain knowledge item."""
    item = KnowledgeItem(
        title=item_in.title,
        content=item_in.content,
        category=item_in.category,
        department_id=item_in.department_id,
        organization_id=item_in.organization_id,
        is_confidential=item_in.is_confidential,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


# --- ACL-enforced knowledge query ---

@router.get("/query", response_model=list[KnowledgeItemResponse])
async def query_knowledge(
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
    category: str | None = None,
    confidential_only: bool = False,
):
    """Query Company Brain knowledge items with ACL enforcement applied.

    Returns only items the current agent is allowed to read:
      * non-confidential items in the agent's organization are readable, or
      * confidential items require an ACL grant (direct agent, department, or
        team membership) with read permission.

    Access is enforced in the query itself, before results are returned.
    """
    agent_id = current_agent.id
    org_id = current_agent.organization_id

    # Agent's department and team memberships (for ACL matching).
    agent_depts = select(DepartmentAgent.department_id).where(
        DepartmentAgent.agent_id == agent_id
    )
    agent_teams = select(DepartmentAgent.team_id).where(
        DepartmentAgent.agent_id == agent_id
    )

    # An ACL grant is applicable when it grants read to this agent directly,
    # or to one of the agent's departments or teams.
    applicable_grant = exists(select(KnowledgeAccess).where(
        KnowledgeAccess.knowledge_item_id == KnowledgeItem.id,
        KnowledgeAccess.permission == "read",
        or_(
            KnowledgeAccess.agent_id == agent_id,
            KnowledgeAccess.department_id.in_(agent_depts),
            KnowledgeAccess.team_id.in_(agent_teams),
        ),
    ))

    query = select(KnowledgeItem).where(
        KnowledgeItem.organization_id == org_id,
        or_(
            KnowledgeItem.is_confidential.is_(False),  # org-wide readable
            applicable_grant,  # ACL-governed readable
        ),
    )

    if category:
        query = query.where(KnowledgeItem.category == category)
    if confidential_only:
        query = query.where(KnowledgeItem.is_confidential.is_(True))

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{item_id}", response_model=KnowledgeItemResponse)
async def get_knowledge_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a knowledge item by ID."""
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge item not found"
        )
    return item


@router.get("/organizations/{org_id}", response_model=list[KnowledgeItemResponse])
async def list_knowledge_items(
    org_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List knowledge items for an organization."""
    result = await db.execute(
        select(KnowledgeItem).where(KnowledgeItem.organization_id == org_id)
    )
    return result.scalars().all()


@router.patch("/{item_id}", response_model=KnowledgeItemResponse)
async def update_knowledge_item(
    item_id: str,
    item_in: KnowledgeItemUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a knowledge item."""
    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge item not found"
        )
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


# --- Knowledge ingestion pipeline (document import + ACL tagging at ingest time) ---

@router.post(
    "/ingest",
    response_model=KnowledgeIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_knowledge_item(
    ingest_in: KnowledgeIngestRequest,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a Company Brain document with ACL tags applied at ingest time.

    Creates the knowledge item and, in the same transaction, creates the
    access grants (ACL) so the document is immediately governed by policy.
    Agents can only ingest into their own organization.
    """
    if str(current_agent.organization_id) != ingest_in.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only ingest into your own organization",
        )

    item = KnowledgeItem(
        title=ingest_in.title,
        content=ingest_in.content,
        category=ingest_in.category,
        department_id=ingest_in.department_id,
        organization_id=ingest_in.organization_id,
        is_confidential=ingest_in.is_confidential,
    )
    db.add(item)
    await db.flush()  # get item.id before creating grants

    grants_created = 0
    for grant in ingest_in.access_grants:
        access = KnowledgeAccess(
            knowledge_item_id=item.id,
            department_id=grant.department_id,
            team_id=grant.team_id,
            agent_id=grant.agent_id,
            permission=grant.permission,
            granted_by=current_agent.id,
        )
        db.add(access)
        grants_created += 1

    await db.commit()
    await db.refresh(item)
    return KnowledgeIngestResponse(
        id=item.id,
        title=item.title,
        access_grants_created=grants_created,
    )


# --- Knowledge access (ACL) ---

@router.post(
    "/access",
    response_model=KnowledgeAccessResponse,
    status_code=status.HTTP_201_CREATED,
)
async def grant_knowledge_access(
    access_in: KnowledgeAccessCreate,
    db: AsyncSession = Depends(get_db),
):
    """Grant access to a knowledge item for a department, team, or agent."""
    access = KnowledgeAccess(
        knowledge_item_id=access_in.knowledge_item_id,
        department_id=access_in.department_id,
        team_id=access_in.team_id,
        agent_id=access_in.agent_id,
        permission=access_in.permission,
        granted_by=access_in.granted_by,
    )
    db.add(access)
    await db.commit()
    await db.refresh(access)
    return access


@router.get("/{item_id}/access", response_model=list[KnowledgeAccessResponse])
async def list_knowledge_access(
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List access grants for a knowledge item."""
    result = await db.execute(
        select(KnowledgeAccess).where(KnowledgeAccess.knowledge_item_id == item_id)
    )
    return result.scalars().all()
