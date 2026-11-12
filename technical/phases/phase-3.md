# Phase 3 - Connectors

- Envelope-encrypted secrets store (Postgres + Vault/KMS; Vault-ready).
- Connectors: HTTP (allowlist + SSRF protection), PostgreSQL (read-only default, parameterized queries only), SMTP email, Playwright MCP (browser automation via MCP proxy).
- MCP gateway/proxy as first-class - route MCP JSON-RPC through gateway, tool discovery with policy enforcement, full audit of all MCP calls (including Playwright).
- Credential broker issues short-lived, scoped leases; agents never receive raw secrets.

Done when: agent does real work via MCP or native connector and never sees a password; all calls go through policy + audit.

## Links

- Prev: [[phase-2]]
- Next: [[phase-4]]
