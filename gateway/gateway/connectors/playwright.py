"""Playwright browser-automation connector via MCP proxy (Phase 3).

Delegates to the MCP gateway/proxy which fronts a Playwright MCP server. All
calls are policy-enforced and audited through the proxy.
"""

from __future__ import annotations

from typing import Any

from gateway.connectors.base import ConnectorBase, ConnectorError


class PlaywrightConnector(ConnectorBase):
    """Playwright connector routed through the MCP proxy.

    Config keys:
      mcp_server: name of the Playwright MCP server (default "playwright")

    Executes by issuing an MCP ``tools/call`` through the gateway proxy.
    """

    connector_type = "playwright"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.mcp_server = self.config.get("mcp_server", "playwright")

    def validate_params(self, params: dict[str, Any]) -> None:
        tool = params.get("mcp_tool")
        if not tool:
            raise ConnectorError("Playwright connector requires an 'mcp_tool' parameter")
        arguments = params.get("arguments")
        if arguments is not None and not isinstance(arguments, dict):
            raise ConnectorError("'arguments' must be an object")

    async def _run(
        self, params: dict[str, Any], secret: str | None = None
    ) -> dict[str, Any]:
        from gateway.mcp.proxy import MCPProxy

        proxy = MCPProxy()
        return await proxy.call(
            server=self.mcp_server,
            method="tools/call",
            params={
                "name": params["mcp_tool"],
                "arguments": params.get("arguments") or {},
            },
            secret=secret,
        )
