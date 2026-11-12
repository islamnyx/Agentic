"""MCP gateway/proxy (Phase 3).

Routes MCP JSON-RPC calls through the gateway so every call is:
  * policy-enforced (tool discovery and invocation),
  * audited (every call recorded via ToolCall),
  * PII-redacted on results before they reach the agent or audit log.

MCP servers are registered as tools with ``connector_type="mcp"`` and their
endpoint URL in ``config`` (JSON). The proxy forwards JSON-RPC to the server
and returns the result. Agents never contact MCP servers directly.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.core.audit import AuditService
from gateway.core.opa import evaluate_policy
from gateway.models.audit_entry import AuditEntry
from gateway.models.tool import Tool
from gateway.models.tool_call import ToolCall


class McpProxyError(Exception):
    """Raised when the MCP proxy cannot complete a call."""


# PII detectors (best-effort, defense-in-depth; not a certified DLP guarantee).
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(
    r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\b"
)
_SSN_RE = re.compile(r"\b\d{3}[-.\s]\d{2}[-.\s]\d{4}\b")
_CARD_RE = re.compile(r"\b(?:\d[ -]?){13,16}\b")


def _mask_email(match: re.Match[str]) -> str:
    email = match.group(0)
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


def _mask_phone(match: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    return f"***-***-{digits[-4:]}" if len(digits) >= 4 else "***"


def _mask_ssn(match: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    return f"***-**-{digits[-4:]}" if len(digits) >= 4 else "***"


def _mask_card(match: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    if 13 <= len(digits) <= 16:
        return f"****-****-****-{digits[-4:]}"
    return match.group(0)


def redact_pii(value: Any) -> Any:
    """Redact PII found anywhere inside ``value`` (strings, dicts, lists).

    Returns a new structure with PII masked. Best-effort defense-in-depth.
    """
    if isinstance(value, str):
        text = _EMAIL_RE.sub(_mask_email, value)
        text = _PHONE_RE.sub(_mask_phone, text)
        text = _SSN_RE.sub(_mask_ssn, text)
        text = _CARD_RE.sub(_mask_card, text)
        return text
    if isinstance(value, dict):
        return {k: redact_pii(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_pii(v) for v in value]
    return value


class MCPProxy:
    """MCP JSON-RPC proxy with policy enforcement, audit, and PII redaction."""

    async def _server_url(
        self, db: AsyncSession, server_name: str
    ) -> str | None:
        result = await db.execute(
            select(Tool).where(
                Tool.name == server_name,
                Tool.connector_type == "mcp",
                Tool.is_active.is_(True),
            )
        )
        tool = result.scalar_one_or_none()
        if not tool or not tool.config:
            return None
        try:
            config = json.loads(tool.config)
        except Exception:
            return None
        return config.get("url")

    def _build_policy_input(
        self, agent, tool: str, method: str, params: dict[str, Any], db: AsyncSession
    ) -> dict[str, Any]:
        scopes = agent.scope_list
        return {
            "who": {
                "agent": {"id": agent.id, "name": agent.name, "scopes": scopes},
                "owner": {"id": agent.owner_id, "role": None},
                "org": {"id": agent.organization_id},
            },
            "what": {
                "tool": tool,
                "action": method,
                "parameters": params,
            },
            "on_what": {
                "resource_type": "mcp_server",
                "resource_id": tool,
                "tenant_id": agent.organization_id,
            },
            "context": {
                "session_id": params.get("session_id", ""),
                "risk_level": params.get("risk_level", "medium"),
                "data_labels": params.get("data_labels", ["internal"]),
            },
        }

    async def _audit(
        self,
        db: AsyncSession,
        agent,
        tool: str,
        method: str,
        params: dict[str, Any],
        decision: str,
        reason: str,
        result: str | None = None,
    ) -> None:
        tool_call = ToolCall(
            agent_id=agent.id,
            tool_id=tool,
            parameters=json.dumps(params),
            result=result,
            decision=decision,
            decision_reason=reason,
        )
        db.add(tool_call)
        # Tamper-evident, hash-chained audit entry for the MCP call.
        audit_service = AuditService()
        await audit_service.append(
            db=db,
            action="mcp.call",
            actor_id=agent.id,
            actor_type="agent",
            resource_type="mcp_server",
            resource_id=tool,
            details={
                "method": method,
                "decision": decision,
                "reason": reason,
                "parameters": params,
            },
        )
        await db.commit()

    async def _resolve_tool_id(self, db: AsyncSession, tool: str) -> str:
        result = await db.execute(select(Tool).where(Tool.name == tool))
        row = result.scalar_one_or_none()
        return str(row.id) if row else tool

    # --- Public API ---

    async def list_tools(
        self,
        db: AsyncSession,
        agent,
        server_name: str,
    ) -> dict[str, Any]:
        """Discover tools on an MCP server, policy-enforced.

        Evaluates a discovery policy before forwarding ``tools/list`` to the
        MCP server. Returns the server's tool list (filtered by policy if
        desired).
        """
        url = await self._server_url(db, server_name)
        if not url:
            raise McpProxyError(f"MCP server {server_name!r} not found or inactive")

        policy_input = self._build_policy_input(
            agent, server_name, "tools/list", {}, db
        )
        decision = await evaluate_policy(policy_input)

        tool_id = await self._resolve_tool_id(db, server_name)
        if decision.deny:
            await self._audit(
                db, agent, tool_id, "tools/list", {}, "denied",
                "; ".join(decision.reasons) or "denied by policy",
            )
            raise McpProxyError(
                "Tool discovery denied: "
                + "; ".join(decision.reasons) or "denied by policy"
            )

        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.RequestError as exc:
            await self._audit(
                db, agent, tool_id, "tools/list", {}, "denied",
                f"MCP server unreachable: {exc}",
            )
            raise McpProxyError(f"MCP server unreachable: {exc}") from exc

        redacted = redact_pii(data)
        await self._audit(
            db, agent, tool_id, "tools/list", {}, "allowed",
            "; ".join(decision.reasons) or "allowed by policy",
            result=json.dumps(redacted),
        )
        return redacted

    async def call(
        self,
        db: AsyncSession,
        agent,
        server_name: str,
        method: str,
        params: dict[str, Any],
        secret: str | None = None,
    ) -> dict[str, Any]:
        """Forward an MCP call to a server, policy-enforced and audited."""
        url = await self._server_url(db, server_name)
        if not url:
            raise McpProxyError(f"MCP server {server_name!r} not found or inactive")

        policy_input = self._build_policy_input(
            agent, server_name, method, params, db
        )
        decision = await evaluate_policy(policy_input)

        tool_id = await self._resolve_tool_id(db, server_name)
        if decision.deny:
            await self._audit(
                db, agent, tool_id, method, params, "denied",
                "; ".join(decision.reasons) or "denied by policy",
            )
            raise McpProxyError(
                "MCP call denied: "
                + "; ".join(decision.reasons) or "denied by policy"
            )
        if decision.require_approval:
            await self._audit(
                db, agent, tool_id, method, params, "require_approval",
                "; ".join(decision.reasons) or "requires approval",
            )
            raise McpProxyError(
                "MCP call requires approval: "
                + "; ".join(decision.reasons) or "requires approval"
            )

        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": method,
            "params": params,
        }
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if secret:
            headers["Authorization"] = f"Bearer {secret}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.RequestError as exc:
            await self._audit(
                db, agent, tool_id, method, params, "denied",
                f"MCP server unreachable: {exc}",
            )
            raise McpProxyError(f"MCP server unreachable: {exc}") from exc

        redacted = redact_pii(data)
        await self._audit(
            db, agent, tool_id, method, params, "allowed",
            "; ".join(decision.reasons) or "allowed by policy",
            result=json.dumps(redacted),
        )
        return redacted
