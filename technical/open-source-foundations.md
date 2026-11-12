# Open Source Foundations — Agent OS

Projects to build on instead of starting from zero. Grouped by component, with GitHub URL, license, and the phase where each is first needed.

## Policy Engine (Security Engine core)

| Project | URL | License | Phase | Role |
|---------|-----|---------|-------|------|
| Open Policy Agent (OPA) | https://github.com/open-policy-agent/opa | Apache-2.0 | Phase 2 | Rego policy engine sidecar; allow/deny/require_approval decisions |
| Microsoft Agent Governance Toolkit | https://github.com/microsoft/agent-governance-toolkit | (see repo) | Phase 2+ | Agent OS policy engine (sub-ms latency), YAML/Rego/Cedar, identity mesh, SRE hooks |

## MCP Gateway / Proxy (Integration Hub + Security Engine)

| Project | URL | License | Phase | Role |
|---------|-----|---------|-------|------|
| MCPGate | https://github.com/BuildWithAbid/mcpgate | MIT | Phase 3 | MCP reverse proxy: auth, rate limiting, access control, observability |
| Bridge MCP Gateway | https://github.com/codingjam/bridge-mcp | (see repo) | Phase 3 | Python 3.12+ MCP gateway, native protocol, session management, Keycloak auth |
| mcp-gateway (r0wi) | https://github.com/R0Wi/mcp-gateway | (see repo) | Phase 3 | FastAPI + FastMCP, YAML config, encrypted SQLite, OAuth 2.1 |
| MCP Auth Gateway | https://github.com/tgandhle/mcp-auth-gateway | MIT | Phase 3 | OAuth 2.1/JWT reverse proxy, per-method scope enforcement, audit logging |
| MCP Audit Gateway | https://github.com/amin-ale/mcp-audit-gateway | MIT | Phase 3/5 | Per-tool RBAC, multi-tenant isolation, PII redaction, tamper-evident audit |
| fast-gateway | https://pypi.org/project/fast-gateway/ | MIT | Phase 3 | FastMCP-based namespaced MCP gateway, hook pipeline (auth/policy/redaction/audit) |
| @playwright/mcp | https://www.npmjs.com/package/@playwright/mcp | (see npm) | Phase 3 | Browser automation MCP server (verified working) |

## Orchestration (Execution Layer)

| Project | URL | License | Phase | Role |
|---------|-----|---------|-------|------|
| LangGraph | https://github.com/langchain-ai/langgraph | MIT | Phase 6 | Stateful agent orchestration, human-in-the-loop, durable execution |
| CrewAI | https://github.com/crewAIInc/crewAI | MIT | Phase 6 | Role-playing multi-agent orchestration (alternative to LangGraph) |

## Agent Studio / Visual Builder (Control Plane — Agent creation)

| Project | URL | License | Phase | Role |
|---------|-----|---------|-------|------|
| Crew AI Studio | https://github.com/Arturski/crew-ai-studio | Apache-2.0 | Phase 7 | No-code visual studio for CrewAI, visual canvas, secrets vault, MCP |
| SmythOS Studio | https://github.com/SmythOS/smythos-studio | MIT | Phase 7 | Drag-and-drop visual agent builder, deployable runtime stack |
| Inkeep Agents | https://github.com/inkeep/agents | (fair-code) | Phase 7 | Visual builder + TypeScript SDK, 2-way sync, MCP tools, credential management |
| LangConfig | https://github.com/LangConfig/langconfig | MIT | Phase 7 | Visual workflow builder for LangChain/LangGraph, drag-and-drop canvas |
| ZeroAgent Studio | https://github.com/sakurablush/zeroagent-studio | MIT | Phase 7 | Browser-based visual agent builder, 203 chainable tools |
| Coze Studio | https://github.com/coze-dev/coze-studio | Apache-2.0 | Phase 7 | All-in-one visual agent platform (prompt, RAG, plugin, workflow) |

## Authentication / Identity

| Project | URL | License | Phase | Role |
|---------|-----|---------|-------|------|
| Keycloak | https://github.com/keycloak/keycloak | Apache-2.0 | Phase 1+ | OIDC identity provider (noted as "skip for now, OIDC-ready") |

## Secrets Management

| Project | URL | License | Phase | Role |
|---------|-----|---------|-------|------|
| HashiCorp Vault | https://github.com/hashicorp/vault | MPL-2.0 | Phase 3 | Envelope-encrypted secrets store (Vault-ready) |

## Observability

| Project | URL | License | Phase | Role |
|---------|-----|---------|-------|------|
| OpenTelemetry | https://github.com/open-telemetry/opentelemetry-python | Apache-2.0 | Phase 5+ | Logs, traces, costs |

## Browser Automation

| Project | URL | License | Phase | Role |
|---------|-----|---------|-------|------|
| @playwright/mcp | https://www.npmjs.com/package/@playwright/mcp | (see npm) | Phase 3 | Browser automation via MCP (verified: initialize + tools/list work) |

## Database / Backend / Frontend (your existing choices)

| Component | Choice | Role |
|-----------|--------|------|
| Backend | Python 3.12 + FastAPI + Pydantic | Gateway API (already scaffolded) |
| Database | PostgreSQL 16 | Registry, policies, audit, approvals |
| Migrations/ORM | Alembic + SQLAlchemy | Schema management |
| Frontend | Next.js + TypeScript | Console UI |
| Background jobs | Redis + Celery | Workflow orchestration |
| Deployment | Docker Compose | Self-hostable from day one |

## Phase Mapping — when to adopt each

| Phase | Focus | Adopt these projects |
|-------|-------|---------------------|
| **Phase 0** (wks 1-2) | Foundations | None external yet — repo, CI, compose, threat model |
| **Phase 1** (wks 3-5) | Gateway skeleton | OPA (sidecar prep), Keycloak (OIDC prep) |
| **Phase 2** (wks 6-8) | Policy engine | **OPA** (primary), Microsoft Agent Governance Toolkit (reference/alternative) |
| **Phase 3** (wks 9-10) | Connectors | **MCPGate / Bridge MCP / mcp-gateway / fast-gateway**, **MCP Audit Gateway**, Vault, **@playwright/mcp** |
| **Phase 4** (wks 11-12) | Approvals | MCP gateways (approval hooks), OPA (approval policies) |
| **Phase 5** (wks 13-14) | Audit | **MCP Audit Gateway**, OpenTelemetry |
| **Phase 6** (wks 15-16) | Cross-step policies | **LangGraph** or CrewAI (orchestration + session-aware rules) |
| **Phase 7** (wks 17-18) | Console | **Crew AI Studio / SmythOS Studio / Inkeep Agents / LangConfig** (visual builder reference or adoption) |

## Recommended "don't start from zero" stack

- **Policy engine:** OPA (open-policy-agent/opa)
- **MCP proxy/gateway:** MCPGate (BuildWithAbid/mcpgate) or fast-gateway
- **MCP audit/RBAC:** MCP Audit Gateway (amin-ale/mcp-audit-gateway)
- **Orchestration:** LangGraph (langchain-ai/langgraph)
- **Agent Studio (optional, Phase 7):** Crew AI Studio (Arturski/crew-ai-studio) or SmythOS Studio
- **Secrets:** Vault (hashicorp/vault)
- **Auth:** Keycloak
- **Observability:** OpenTelemetry
- **Browser automation:** @playwright/mcp

All projects above are OSI-approved open source (Apache-2.0 / MIT / MPL-2.0) except Inkeep Agents (fair-code) and n8n (source-available, not OSI).
