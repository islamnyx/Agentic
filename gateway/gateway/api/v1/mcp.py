"""MCP proxy routes (Phase 3).

Proxies MCP JSON-RPC calls through the gateway so every call is policy
enforced and audited. Agents never contact MCP servers directly.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.api.deps import get_current_agent, get_db
from gateway.mcp.proxy import MCPProxy, McpProxyError

router = APIRouter()


@router.post("/mcp/{server}", status_code=status.HTTP_200_OK)
async def mcp_proxy(
    server: str,
    body: dict,
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Proxy an MCP JSON-RPC call through the gateway.

    Body: {"jsonrpc": "2.0", "id": <id>, "method": "<method>", "params": {...}}
    """
    method = body.get("method")
    params = body.get("params") or {}
    if not method:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="method is required"
        )

    proxy = MCPProxy()
    try:
        return await proxy.call(
            db=db,
            agent=current_agent,
            server_name=server,
            method=method,
            params=params,
        )
    except McpProxyError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
