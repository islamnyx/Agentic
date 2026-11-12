"""Tool registry and invoke routes.

Phase 1: tool registry (native tools + MCP tools) and a plain pass-through
invoke endpoint with logging. Every invoke is recorded as a ToolCall.

Phase 2: every invoke is evaluated by the OPA policy engine before execution.
The decision (allowed / denied / require_approval) and deny reasons are logged
to the ToolCall record and returned to the caller.
"""

from gateway.core.session_context import get_session_context_service
from gateway.models.session_context import TrustLabel
import json as _json


CONNECTOR_TYPES = {"http", "postgres", "smtp", "playwright"}

router = APIRouter()

MOCK_RESULTS: dict[str, dict[str, Any]] = {
    "read_invoices": lambda params: {
        "invoices": [
            {"id": "inv-001", "amount": 1250.00, "status": "paid"},
            {"id": "inv-002", "amount": 430.00, "status": "open"},
        ],
        "count": 2,
        "echo": params,
    },
    "query_db": lambda params: {
        "rows": [{"id": 1, "name": "sample-row"}],
        "row_count": 1,
        "echo": params,
    },
    "email_customers": lambda params: {
        "sent": True,
        "message_id": str(uuid.uuid4()),
        "echo": params,
    },
    "issue_refunds": lambda params: {
        "refunded": True,
        "amount": params.get("amount"),
        "currency": params.get("currency", "USD"),
        "echo": params,
    },
}


def _mock_result(tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    generator = MOCK_RESULTS.get(tool_name)
    if generator:
        return generator(parameters)
    return {"status": "ok", "tool": tool_name, "echo": parameters}


async def _build_policy_input(
    agent: Agent,
    tool: str,
    action: str,
    parameters: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """Build the normalized policy input (who/what/on_what/context) for OPA."""
    scopes = agent.scope_list

    # Resolve owner role for the `who.owner` block.
    owner_role = None
    if agent.owner_id:
        result = await db.execute(select(User).where(User.id == agent.owner_id))
        owner = result.scalar_one_or_none()
        if owner:
            owner_role = owner.role

    # Resource / tenant context carried on the invocation parameters.
    resource_type = parameters.get("resource_type")
    resource_id = parameters.get("resource_id")
    tenant_id = parameters.get("tenant_id") or agent.organization_id

    data_labels = parameters.get("data_labels", ["internal"])
    if isinstance(data_labels, str):
        data_labels = [data_labels]

    risk_level = parameters.get("risk_level", "medium")
    session_id = parameters.get("session_id", str(uuid.uuid4()))

    return {
        "who": {
            "agent": {
                "id": agent.id,
                "name": agent.name,
                "scopes": scopes,
            },
            "owner": {
                "id": agent.owner_id,
                "role": owner_role,
            },
            "org": {
                "id": agent.organization_id,
            },
        },
        "what": {
            "tool": tool,
            "action": action,
            "parameters": parameters,
        },
        "on_what": {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "tenant_id": tenant_id,
        },
        "context": {
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "risk_level": risk_level,
            "data_labels": data_labels,
        },
    }


# --- Tool registry ---

@router.post("/", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    tool_in: ToolCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new tool (native or MCP)."""
    result = await db.execute(select(Tool).where(Tool.name == tool_in.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tool already registered",
        )
    tool = Tool(
        name=tool_in.name,
        description=tool_in.description,
        connector_type=tool_in.connector_type,
        config=tool_in.config,
        is_active=tool_in.is_active,
    )
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    return tool


@router.get("/", response_model=list[ToolResponse])
async def list_tools(
    db: AsyncSession = Depends(get_db),
):
    """List all registered tools."""
    result = await db.execute(select(Tool))
    return result.scalars().all()


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a registered tool by ID."""
    result = await db.execute(select(Tool).where(Tool.id == str(tool_id)))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )
    return tool


# --- Invoke ---

@router.post("/{tool}/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(
    tool: str,
    invoke: ToolInvokeRequest,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Invoke a registered tool, governed by the OPA policy engine."""
    result = await db.execute(
        select(Tool).where(Tool.name == tool, Tool.is_active.is_(True))
    )
    db_tool = result.scalar_one_or_none()
    if not db_tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found or inactive",
        )

    # Propagate trust labels from parameters/session to session context if present
    try:
        session_service = get_session_context_service()
        session_id = invoke.parameters.get("session_id") or policy_input.get("context", {}).get("session_id")
        if session_id:
            # Create/get session if we have agent context
            await session_service.get_or_create_session(
                db=db,
                session_id=str(session_id),
                agent_id=current_agent.id,
                organization_id=current_agent.organization_id,
            )
            # Add labels from parameters
            data_labels = invoke.parameters.get("data_labels") or policy_input.get("context", {}).get("data_labels")
            if data_labels:
                if isinstance(data_labels, str):
                    data_labels = [data_labels]
                for lbl in data_labels:
                    try:
                        # Normalize enum/string
                        lbl_str = lbl.value if hasattr(lbl, "value") else str(lbl)
                        await session_service.add_label_to_session(db, str(session_id), lbl_str)
                    except Exception:
                        pass
    except Exception:
        pass

    action = invoke.parameters.get("action", "read")

    # Dry-run: decision is logged but never enforced.
    if settings.POLICY_DRY_RUN:
        decision.reasons = ["dry-run: decision not enforced"] + decision.reasons

    if decision.deny:
        tool_call = ToolCall(
            id=str(uuid.uuid4()),
            agent_id=current_agent.id,
            tool_id=db_tool.id,
            parameters=parameters_json,
            result=None,
            decision="denied",
            decision_reason="; ".join(decision.reasons) or "denied by policy",
        )
        db.add(tool_call)
        await db.commit()
        await db.refresh(tool_call)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "decision": "denied",
                "reasons": decision.reasons,
                "tool_call_id": tool_call.id,
            },
        )

    if decision.require_approval:
        parameters_hash = Approval.hash_parameters(invoke.parameters)
        delegation_chain = json.dumps(
            {
                "requesting_agent": {
                    "id": current_agent.id,
                    "name": current_agent.name,
                },
                "session_id": invoke.parameters.get("session_id"),
                "organization_id": current_agent.organization_id,
                "owner_id": current_agent.owner_id,
            },
            sort_keys=True,
        )
        now = datetime.now(timezone.utc)

        # Look for an existing valid, approved approval for this exact
        # invocation (same agent, tool, parameter hash).
        result = await db.execute(
            select(Approval).where(
                Approval.agent_id == current_agent.id,
                Approval.tool_id == db_tool.id,
                Approval.parameters_hash == parameters_hash,
                Approval.status == "approved",
                Approval.expires_at > now,
            )
        )
        existing_approval = result.scalar_one_or_none()

        if existing_approval and existing_approval.is_usable:
            # Single-use enforcement: consume the approval on execution.
            existing_approval.status = "used"
            await db.commit()
            # Fall through to execution below.
        else:
            # No usable approval: check for a pending one, otherwise create one.
            result = await db.execute(
                select(Approval).where(
                    Approval.agent_id == current_agent.id,
                    Approval.tool_id == db_tool.id,
                    Approval.parameters_hash == parameters_hash,
                    Approval.status == "pending",
                    Approval.expires_at > now,
                )
            )
            pending_approval = result.scalar_one_or_none()
            if pending_approval:
                # Already waiting for a human decision.
                tool_call = ToolCall(
                    id=str(uuid.uuid4()),
                    agent_id=current_agent.id,
                    tool_id=db_tool.id,
                    parameters=parameters_json,
                    result=None,
                    decision="require_approval",
                    decision_reason="; ".join(decision.reasons) or "requires approval",
                )
                db.add(tool_call)
                await db.commit()
                await db.refresh(tool_call)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "decision": "require_approval",
                        "reasons": decision.reasons,
                        "tool_call_id": tool_call.id,
                        "approval_id": pending_approval.id,
                    },
                )

            # Create a new pending approval (delegation chain recorded).
            ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            approval = Approval(
                agent_id=current_agent.id,
                tool_id=db_tool.id,
                action=action,
                parameters_hash=parameters_hash,
                parameters_json=parameters_json,
                delegation_chain=delegation_chain,
                status="pending",
                expires_at=now + timedelta(seconds=ttl),
            )
            db.add(approval)
            tool_call = ToolCall(
                id=str(uuid.uuid4()),
                agent_id=current_agent.id,
                tool_id=db_tool.id,
                parameters=parameters_json,
                result=None,
                decision="require_approval",
                decision_reason="; ".join(decision.reasons) or "requires approval",
            )
            db.add(tool_call)
            await db.commit()
            await db.refresh(approval)
            await db.refresh(tool_call)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "decision": "require_approval",
                    "reasons": decision.reasons,
                    "tool_call_id": tool_call.id,
                    "approval_id": approval.id,
                },
            )

    # Allowed: execute the tool. Native tools return mock results; connector
    # types (http, postgres, smtp, playwright) execute for real using a secret
    # injected via a credential lease -- the agent never sees the secret.
    if db_tool.connector_type in CONNECTOR_TYPES:
        if not invoke.lease_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connector tool requires a lease_token",
            )
        try:
            payload = jwt.decode(
                invoke.lease_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid lease token: {exc}",
            ) from exc

        result = await db.execute(
            select(ConnectorCredential).where(
                ConnectorCredential.id == payload.get("credential_id")
            )
        )
        credential = result.scalar_one_or_none()
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found",
            )
        if str(credential.organization_id) != str(current_agent.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not your organization's credential",
            )
        if credential.connector_type != db_tool.connector_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Credential connector type "
                    f"{credential.connector_type} does not match tool "
                    f"{db_tool.connector_type}"
                ),
            )

        broker = CredentialBroker()
        try:
            secret = await broker.get_secret(invoke.lease_token, current_agent, db=db)
        except Exception as exc:  # LeaseError or validation failure
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot obtain credential: {exc}",
            ) from exc

        try:
            tool_config = (
                json.loads(db_tool.config) if db_tool.config else None
            )
            connector = build_connector(db_tool.connector_type, tool_config)
            connector_result = await connector.execute(
                invoke.parameters, secret
            )
        except Exception as exc:
            tool_call = ToolCall(
                id=str(uuid.uuid4()),
                agent_id=current_agent.id,
                tool_id=db_tool.id,
                parameters=parameters_json,
                result=None,
                decision="allowed",
                decision_reason=f"connector execution failed: {exc}",
            )
            db.add(tool_call)
            await db.commit()
            await db.refresh(tool_call)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"decision": "allowed", "error": str(exc),
                        "tool_call_id": tool_call.id},
            ) from exc

        tool_call = ToolCall(
            id=str(uuid.uuid4()),
            agent_id=current_agent.id,
            tool_id=db_tool.id,
            parameters=parameters_json,
            result=json.dumps(connector_result),
            decision="allowed",
            decision_reason="; ".join(decision.reasons) or "allowed by policy",
        )
        db.add(tool_call)
        await db.commit()
        await db.refresh(tool_call)

        return ToolInvokeResponse(
            decision="allowed",
            reason="; ".join(decision.reasons) or "allowed by policy",
            result=connector_result,
            tool_call_id=uuid.UUID(tool_call.id),
        )

    # Native tools: mock result (Phase 1 behaviour).
    mock_result = _mock_result(tool, invoke.parameters)
    tool_call = ToolCall(
        id=str(uuid.uuid4()),
        agent_id=current_agent.id,
        tool_id=db_tool.id,
        parameters=parameters_json,
        result=json.dumps(mock_result),
        decision="allowed",
        decision_reason="; ".join(decision.reasons) or "allowed by policy",
    )
    db.add(tool_call)
    await db.commit()
    await db.refresh(tool_call)

    return ToolInvokeResponse(
        decision="allowed",
        reason="; ".join(decision.reasons) or "allowed by policy",
        result=mock_result,
        tool_call_id=uuid.UUID(tool_call.id),
    )
