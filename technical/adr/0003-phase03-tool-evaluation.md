# ADR-0003: Phase 03 third-party tool evaluation (Vault, MCP gateway, MCP audit/RBAC)

## Context

Phase 03's todo.md listed three open evaluation items:

1. HashiCorp Vault evaluation (production secrets / envelope-encryption KEK)
2. MCP gateway selection: MCPGate (BuildWithAbid/mcpgate) vs fast-gateway
3. MCP audit/RBAC: amin-ale/mcp-audit-gateway

These are evaluation/selection tasks about external tools, not feature-implementation tasks. Our gateway already implements their core functionality natively:

* Vault-ready KEK → `gateway/core/crypto.py` (`_VaultKek` calls Vault Transit `encrypt`/`decrypt`; local HKDF KEK fallback for dev)
* MCP proxy/gateway → `gateway/mcp/proxy.py` (FastAPI-native, JSON-RPC routing, OPA policy enforcement, `ToolCall` audit)
* Audit/RBAC → OPA policies + `gateway/core/broker.py` scoped leases + `ToolCall` audit

This ADR records the decisions for each item.

---

## Decision 1: HashiCorp Vault — adopt the transit KEK pattern, local fallback for dev

### Research

Vault Transit secrets engine exposes `POST /v1/transit/encrypt/:name` and
`POST /v1/transit/decrypt/:name` (HashiCorp Vault HTTP API). The gateway's
`_VaultKek` (gateway/core/crypto.py:44) wraps/unwraps data encryption keys
(DEKs) through these endpoints, so the KEK never leaves Vault. Envelope
encryption: a random DEK (AES-256-GCM) encrypts each secret; the DEK is then
wrapped by the KEK. The stored envelope holds `ciphertext`, `nonce`,
`wrapped_dek`, `key_id`, `kek_source`.

### Decision

Adopt Vault Transit as the production KEK source, with a locally HKDF-derived
KEK (from `SECRET_KEY`) as the development fallback. `EnvelopeEncryption`
auto-selects Vault when `VAULT_ADDR` and `VAULT_TOKEN` are set, otherwise
falls back to the local KEK so the gateway boots in dev without Vault.

### Rationale

* Keeps the master KEK out of the application process (Vault holds it).
* Matches the threat model: agents never see raw secrets; the KEK is used only
  to wrap/unwrap DEKs.
* Dev/CI can run without Vault via the local fallback (no infra dependency for
  tests).

### Open (not implemented)

* Vault operator deployment, unseal, auth method (Kubernetes/JWT/OIDC), and
  transit key rotation policy are deployment concerns for Phase 04/05, not
  gateway code.

---

## Decision 2: MCP gateway selection — keep the native FastAPI proxy; do not adopt MCPGate or fast-gateway

### Research

* **MCPGate** (BuildWithAbid/mcpgate, PyPI `mcpgate` 0.4.0): open-source MCP
  reverse proxy with auth, rate limiting, access control, observability. Turns
  OpenAPI specs into MCP tools. Stateless.
* **fast-gateway** (niradler, PyPI `fast-gateway` 0.0.5): built on FastMCP +
  FastAPI, mounts on FastAPI, turns a registry of upstream MCP servers into one
  governed, namespaced MCP endpoint. Plugin system for audit/rate limiting.
  Python 3.11+, MIT.

### Decision

Keep the native `gateway/mcp/proxy.py` FastAPI-based MCP proxy. Do not adopt
MCPGate or fast-gateway as a replacement.

### Rationale

* Our proxy is already FastAPI-native, shares the same dependency injection,
  DB session, OPA policy input schema, and `ToolCall` audit table as the rest
  of the gateway. Adopting an external gateway would duplicate routing,
  auth, and audit and introduce a second trust boundary.
* fast-gateway's plugin model and FastMCP base are conceptually similar to our
  proxy, but integrating it would mean running two MCP proxies and mapping
  their concepts onto our OPA policies and `ToolCall` audit — more complexity
  for equivalent coverage.
* MCPGate is a separate service (not a library we import), so adopting it
  would add an operational dependency without reducing gateway code.

We may revisit if we need a standalone, language-agnostic MCP reverse proxy
deployed independently of the FastAPI gateway.

---

## Decision 3: MCP audit/RBAC — implement natively; amin-ale/mcp-audit-gateway is a reference, not a dependency

### Research

**amin-ale/mcp-audit-gateway** (PyPI `mcp-audit-gateway` 0.1.0, MIT):
per-tool RBAC, multi-tenant isolation, PII redaction on tool results,
tamper-evident audit logging (JSONL), per-tenant rate limits, HMAC request
signing. Proxies `tools/list` and `tools/call`, namespaces tools as
`<upstream>.<tool>`, deny-always-wins RBAC, tenant kill-switches, fully
offline test suite.

### Decision

Implement audit/RBAC natively in the gateway (OPA policies + `ToolCall` audit
+ scoped credential leases) and add PII redaction to `MCPProxy.call` /
`list_tools` results (gateway/mcp/proxy.py). Treat amin-ale/mcp-audit-gateway
as a reference implementation, not a dependency.

### Rationale

* OPA already provides allow/deny/require_approval decisions with the
  who/what/on_what/context input schema used across all gateway tools (Phase 2).
* `ToolCall` audit already records every agent tool call with decision + reason
  + result (redacted now via PII redaction).
* `CredentialBroker` already issues short-lived scoped leases so agents never
  receive raw secrets.
* Adding PII redaction to the proxy (emails, phones, SSNs, card numbers)
  covers the amin-ale PII-redaction requirement without a new service.

### PII redaction added

`redact_pii()` recursively masks emails, phone numbers, SSNs, and payment-card
numbers in MCP results before they are returned to the agent and before the
result is written to the `ToolCall` audit log. Best-effort defense-in-depth,
not a certified DLP guarantee (consistent with amin-ale's own caveat).

---

## Consequences

* Production secret management can be switched on by setting `VAULT_ADDR` /
  `VAULT_TOKEN`; no code change required.
* No new external MCP gateway service to deploy or operate.
* PII redaction runs on every MCP proxy result (small CPU cost, defense in
  depth).
