# Architecture — Integration Hub & Secure Execution Gateway

Reusable connectors and consistent access to business systems. All connectors route through the Secure Execution Gateway, which is the enforcement point: protected actions cannot bypass it with direct credentials or alternative integrations.

## Connectors

| Connector | Purpose | Security notes |
|-----------|---------|----------------|
| HTTP API | Call REST/JSON endpoints | Allowlist, no private IP ranges, no redirects by default (SSRF protection) |
| PostgreSQL | Read-only parameterized queries | Read-only default, parameterized queries only |
| SMTP | Send email | Policy-evaluated before send, approval for high-risk |
| Playwright MCP | Browser automation via MCP | Routed through MCP proxy, tool discovery with policy enforcement, full audit |

## MCP Proxy

All MCP JSON-RPC traffic (including Playwright MCP) routes through the gateway MCP proxy. Tool discovery is policy-enforced and every MCP call is audited to the hash-chained audit log.

## Secure Execution Gateway

Intercepts every tool call to a protected business system. Evaluates identity, permissions, and policy (OPA) before allowing, denying, or requesting approval. This is the enforcement boundary of Eclipse.

## Links

- Parent: [[modules]]
- Strategy: [[../../../../planning/architecture/modules]]
