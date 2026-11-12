# MVP Todo List — Eclipse Agent OS (Independent Control Plane)

Eclipse is the independent Agent Control Plane that governs AI agents across providers (Gemini, Claude, OpenAI, n8n, custom, MCP). The MVP is a narrow, focused control plane — not a visual agent builder.

## Phase 0 - Foundations

### Repo & infra
- [x] Set up repo, CI, Compose skeleton (docker-compose, FastAPI gateway, GitHub Actions, pytest)
- [x] Define coding standards and ADRs (CONTRIBUTING.md, adr/0001-repo-skeleton.md)
- [x] Define policy input JSON schema (contract) (gateway/schemas/policy-input.json)

### Threat model & demo
- [x] Write threat model draft (token theft, policy tampering, audit tampering, confused deputy, SSRF, tenant isolation)
- [ ] Review threat model with whole team
- [x] Fix demo scenario (finance/ops agent: read invoices, query DB, email customers, issue refunds)
- [x] Write attack script for demo (scripts/attack_demo.py)
- [ ] Schedule first 5 customer interviews

### Done when: repo runs `docker compose up` and threat model reviewed by everyone.

---

## Phase 1 - Gateway Skeleton (Control Plane Core)

### Agent registry & identity (multi-provider)
- [x] Agent registry (organizations, users, agents tables) — supports registration from any framework
- [x] Departments & teams tables (departments, teams, department_agents) — agents organized into departments
- [x] Company Brain tables (knowledge_items, knowledge_access) — shared knowledge layer with per-item access permissions (deprioritized vs. governance)
- [x] Short-lived signed tokens (JWT, agent-scoped)
- [x] Token rotation and revocation (revocation lists, agents.revoked_at)
- [x] Keycloak prep for OIDC (configured but not yet active — OIDC-ready)

### Tool registry & invoke
- [x] Tool registry (native tools + MCP tools)
- [x] Invoke endpoint (pass-through with logging)
- [x] Mock tools for tests

### Test
- [x] Test: agent registers, calls mock tool, call recorded

### Done when: a test agent registers, calls a mock tool, call recorded.

---

## Phase 2 - Policy Engine

### OPA integration (open-policy-agent/opa)
- [x] OPA sidecar integration (docker-compose service)
- [x] Stable policy input schema (who/what/on_what/context contract)
- [x] First Rego policies (allow, deny, require_approval)
- [x] Department-scoped policies (cross-department agent calls require explicit approval)
- [x] Knowledge ACL policies (per-item read/write enforcement; sales agent cannot read HR/finance items)
- [x] Policy versions stored in Postgres
- [x] Dry-run (simulate) mode
- [x] Deny reasons in API response
- [x] Policy unit tests in CI
- [x] Microsoft Agent Governance Toolkit review (alternative/reference — sub-ms policy engine)

### Test
- [x] Test: same call allowed/denied by policy, deny reason logged

### Done when: same call allowed or denied depending on policy, deny reason logged.

---

## Phase 3 - Connectors & Secure Execution Gateway

### Secrets store
- [x] Envelope-encrypted secrets store (Postgres + Vault-ready KEK)
- [x] HashiCorp Vault evaluation (hashicorp/vault — production secrets)

### MCP proxy/gateway (Integration Hub + Security Engine)
- [x] MCP gateway/proxy as first-class (route MCP JSON-RPC through gateway)
- [x] MCP tool discovery with policy enforcement
- [x] Full audit of all MCP calls (hash-chained AuditEntry)
- [x] MCP gateway selection: MCPGate (BuildWithAbid/mcpgate) or fast-gateway
- [x] MCP audit/RBAC: MCP Audit Gateway (amin-ale/mcp-audit-gateway)

### Native connectors (routed through Secure Execution Gateway)
- [x] HTTP connector (allowlist, SSRF protection, no private IP ranges)
- [x] PostgreSQL connector (read-only default, parameterized queries)
- [x] SMTP email connector
- [x] Playwright MCP browser automation connector (@playwright/mcp via MCP proxy)
- [x] Company Brain ingestion pipeline (document import, ACL tagging at ingest time)
- [x] Knowledge query API with ACL enforcement applied before results returned

### Credential broker
- [x] Credential broker issues short-lived, scoped leases; agents never receive raw secrets

### Test
- [x] Test: agent does real work via MCP or native connector and never sees a password; all calls go through policy + audit

### Done when: agent does real work via MCP or native connector and never sees a password; all calls go through policy + audit.

---

## Phase 4 - Approvals

### Approval flow
- [x] Pending state
- [x] Approver queue
- [x] Approve/deny with timeout
- [x] Approval bound to exact params (hash) + full delegation chain context
- [x] Approval expiry and single-use enforcement (invalidates on param change, prevents reuse)
- [x] Reusable approval platform: bind approval to exact action + parameters, record who approved (payments, discounts, email campaigns, record deletion)
- [x] MCP gateway approval hooks (pre-tool-call gating)
- [x] OPA approval policies (require_approval decisions)

### Emergency kill switch
- [x] Emergency kill switch (revoke tokens immediately — seconds)

### Test
- [x] Test: refund above threshold pauses; changing amount invalidates approval

### Done when: refund above threshold pauses until human approves; changing amount invalidates approval.

---

## Phase 5 - Audit (Complete)

### Hash-chained audit
- [x] Hash-chained audit log (prev_hash, hash per row)
- [x] Ed25519 signature on periodic signed roots
- [x] Verify CLI (detects tampering)
- [x] Export to JSON
- [x] Optional external hash anchoring
- [x] Business metrics tables (dashboard_metrics, security_incidents, agent_costs) feeding Control Center dashboards

### MCP audit integration
- [x] MCP Audit Gateway integration (per-tool RBAC, tamper-evident audit, PII redaction)

### Observability
- [x] OpenTelemetry integration (logs, traces, costs)

### Test
- [x] Test: editing a DB row detected by verification

### Done when: editing a DB row detected by verification.

---

## Phase 6 - Cross-Step Policies

### Trust labels & session-aware rules
- [ ] Trust labels on data (internal, customer-supplied, web)
- [ ] Carry labels through session
- [ ] Session-aware rules (untrusted -> external send -> require approval)
- [ ] LangGraph integration (stateful orchestration, human-in-the-loop, durable execution)
- [ ] CrewAI evaluation (alternative multi-agent orchestration)

### Test
- [ ] Test: invoice-injection attack blocked by session-aware rule, not keyword

### Done when: invoice-injection attack from demo blocked by session-aware rule.

---

## Phase 7 - Console (Control Center)

### Control Center pages (Next.js + TypeScript) — PRIMARY MVP EXPERIENCE
- [ ] Agents page (multi-provider registry, identity, permissions)
- [ ] Policies page
- [ ] Live activity page
- [ ] Approvals queue page
- [ ] Audit page with verify button
- [ ] Kill switch control

### Agent OS Control Center (governance for IT/security teams)
- [ ] Agent identities and scoped permissions page (multi-provider)
- [ ] Company Brain knowledge items + access-control lists page (deprioritized)
- [ ] Approvals history page (bound to exact action + parameters, who approved)
- [ ] Monitoring page: work completed, pending approvals, failed tasks, security incidents, agent costs

### Integration SDK (build after Control Center)
- [ ] SDK and APIs to connect existing agents to Eclipse
- [ ] Agent onboarding guide (Gemini, Claude, OpenAI, n8n, custom Python, MCP)
- [ ] Developer documentation and examples

### Agent OS Studio (DEFERRED — post-MVP)
- [ ] Visual builder for agent instructions, model, tools, knowledge and workflow
- [ ] Department templates (Sales, Support, Finance, HR)
- [ ] SDK and APIs to create, configure and deploy agents

### Business outcome dashboards (for business owners)
- [ ] Work completed by agents
- [ ] Money saved / revenue generated where measurable
- [ ] Pending approvals
- [ ] Failed tasks
- [ ] Security incidents
- [ ] Agent costs

### Agent Studio / visual builder (reference or adoption — DEFERRED)
- [ ] Crew AI Studio evaluation (no-code visual studio for CrewAI)
- [ ] SmythOS Studio evaluation (drag-and-drop visual agent builder)
- [ ] LangConfig evaluation (visual workflow builder for LangChain/LangGraph)
- [ ] Inkeep Agents evaluation (visual builder + TypeScript SDK, 2-way sync)

### Done when: Control Center pages functional; Integration SDK documented; business dashboard shows outcomes not just logs.

---

## Phase 8 - Red-Team & Hardening

### Security testing
- [ ] Prompt-injection test suite (automated)
- [ ] Before/after report
- [ ] Pen-test gateway against Phase 0 threat model

### Delivery
- [ ] Documentation and install guide
- [ ] Recorded demo

### Done when: red-team demo passes; documentation complete.

---

## Cross-Cutting Security (all phases)

- [ ] Rate limiting and per-agent budgets
- [ ] Strict input validation on every connector
- [ ] HTTP connector: allowlist, no private IP ranges, no redirects by default
- [ ] Tenant isolation tests from start
- [ ] Knowledge ACL tests: sales agent cannot read HR/finance knowledge items
- [ ] Department isolation tests: cross-department calls require policy approval
- [ ] Dependency pinning and scanning
- [ ] Secrets scanning in CI
- [ ] Policy changes audited and approval-gated

---

## MVP Acceptance Criteria (Updated for Independent Control Plane)

- [ ] Agent registered from any supported framework (Gemini, Claude, OpenAI, n8n, custom, MCP) with scoped identity and full delegation chain, revoked in seconds
- [ ] No tool call reaches a business system without a logged policy decision via the Secure Execution Gateway
- [ ] Agents never receive real credentials; all secrets brokered via gateway with envelope encryption
- [ ] MCP tool calls governed with same policy enforcement as native connectors
- [ ] High-risk actions pause for a human; approval bound to exact parameters and visible with full context (Slack/console)
- [ ] Audit log uses hash-chained entries with signed roots; verification CLI/tool detects tampering
- [ ] Delegation chain provably recorded for every action (who authorized what)
- [ ] Demo prompt-injection attack blocked, report shows why with full audit trail
- [ ] Deploys with one command on customer's own machine (Docker Compose)
- [ ] Company Brain knowledge item access enforced by per-item ACLs (sales agent cannot read HR/finance items)
- [ ] Department-scoped agent registration enforced; cross-department calls require policy approval
- [ ] Business dashboard shows work completed, pending approvals, failed tasks, security incidents, and agent costs
- [ ] Multi-provider governance: single policy set applies across Gemini, Claude, OpenAI, n8n, custom agents
- [ ] Independent execution enforcement: agents cannot bypass gateway with direct credentials
- [ ] Unified observability: one audit trail for agent activity across all supported providers

---

## Links

- Validated by: [[phases/phase-8]]
- Required by: [[../../planning/go-to-market/phases]]
- Strategic pivot: [[../planning/company/vision]]