"""HTTP connector with SSRF protection and host allowlist (Phase 3)."""

from __future__ import annotations

import ipaddress
import socket
from typing import Any

import httpx

from gateway.connectors.base import ConnectorBase, ConnectorError

# Private / reserved IP ranges that must never be reachable from outbound
# connector calls (SSRF protection). Includes link-local (cloud metadata).
_PRIVATE_RANGES = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("fc00::/7"),
]


def _is_private_ip(host: str) -> bool:
    """Return True if ``host`` resolves to a private/reserved IP."""
    try:
        infos = socket.getaddrinfo(host, None, 0, socket.SOCK_STREAM)
    except OSError:
        # Cannot resolve: treat as unsafe rather than allowing.
        return True
    for _, _, _, _, sockaddr in infos:
        ip = sockaddr[0]
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if any(addr in net for net in _PRIVATE_RANGES):
            return True
    return False


class HttpConnector(ConnectorBase):
    """HTTP(S) connector.

    Config keys:
      allowlist: list of allowed hosts (required)
      methods: allowed HTTP methods (default GET, POST)
      default_timeout: request timeout in seconds (default 30)
      allowed_ports: allowed destination ports (default 80, 443, 8000, 8080)
    """

    connector_type = "http"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.allowlist = set(self.config.get("allowlist", []))
        self.methods = {
            m.upper() for m in self.config.get("methods", ["GET", "POST"])
        }
        self.timeout = float(self.config.get("default_timeout", 30))
        self.allowed_ports = set(
            self.config.get("allowed_ports", [80, 443, 8000, 8080])
        )

    def validate_params(self, params: dict[str, Any]) -> None:
        url = params.get("url")
        if not url:
            raise ConnectorError("HTTP connector requires a 'url' parameter")
        method = str(params.get("method", "GET")).upper()
        if method not in self.methods:
            raise ConnectorError(f"HTTP method {method} not allowed")

        try:
            parsed = httpx.URL(url)
        except Exception as exc:
            raise ConnectorError(f"Invalid URL: {exc}") from exc

        if parsed.scheme.lower() not in ("http", "https"):
            raise ConnectorError("Only http and https schemes are allowed")

        host = parsed.host
        if not host:
            raise ConnectorError("URL must include a host")
        if host not in self.allowlist:
            raise ConnectorError(f"Host {host} is not on the allowlist")

        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        if port not in self.allowed_ports:
            raise ConnectorError(f"Port {port} is not allowed")

        if _is_private_ip(host):
            raise ConnectorError(f"Host {host} resolves to a private/reserved IP")

    async def _run(
        self, params: dict[str, Any], secret: str | None = None
    ) -> dict[str, Any]:
        method = str(params.get("method", "GET")).upper()
        url = params["url"]
        headers = dict(params.get("headers", {}))
        if secret:
            # ``secret`` is injected (e.g. a bearer token); never echoed back.
            headers.setdefault("Authorization", f"Bearer {secret}")
        json_body = params.get("json")
        data = params.get("data")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.request(
                    method, url, headers=headers, json=json_body, content=data
                )
            except httpx.RequestError as exc:
                raise ConnectorError(f"HTTP request failed: {exc}") from exc

        try:
            body = resp.json()
        except Exception:
            body = resp.text

        return {
            "status": resp.status_code,
            "body": body,
            "headers": dict(resp.headers),
        }
