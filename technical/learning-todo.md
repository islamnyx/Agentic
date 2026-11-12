# Learning Checklist — Concepts to Master for Agent OS

As second-year college students, check off each item as you understand it AND use it in code. Learn just-in-time for each phase — don't learn everything before coding.

## 1. Programming Fundamentals

- [ ] Python 3.12+ (async/await, type hints, Pydantic) — Backend gateway is Python/FastAPI
- [ ] TypeScript (strict mode, interfaces, generics) — Frontend Next.js + agent SDK
- [ ] JavaScript/ES6+ (async/await, modules, fetch) — Frontend + MCP clients
- [ ] JSON (schema, validation, serialization) — API contracts, policy input, MCP messages
- [ ] Git (branches, PRs, commits, merging) — Code collaboration, ADRs, version control

## 2. Web & API Concepts

- [ ] HTTP (methods, status codes, headers, CORS) — Gateway API, connector calls
- [ ] REST API design (endpoints, resources, idempotency) — Gateway invoke endpoint, admin APIs
- [ ] JSON-RPC 2.0 (MCP protocol) — MCP server/client communication
- [ ] WebSockets / SSE (server-sent events) — Live activity console, MCP streaming
- [ ] Webhooks (Slack/Teams approvals) — Approval notifications
- [ ] API authentication (Bearer tokens, API keys) — Agent tokens, service auth

## 3. Backend Framework (FastAPI + Python)

- [ ] FastAPI (route decorators, dependency injection, request/response models) — Gateway server
- [ ] Pydantic (data validation, settings management) — Policy input schema, request validation
- [ ] SQLAlchemy 2.0 async ORM (models, sessions, queries) — PostgreSQL interactions
- [ ] Alembic (database migrations) — Schema evolution across phases
- [ ] asyncpg (async PostgreSQL driver) — Async DB access
- [ ] Uvicorn (ASGI server) — Running the gateway

## 4. Database (PostgreSQL)

- [ ] SQL (SELECT, INSERT, UPDATE, DELETE, JOINs, indexes) — All data storage
- [ ] Relational modeling (tables, foreign keys, constraints) — Organizations, agents, tokens, audit_events
- [ ] Row-level security (tenant isolation) — Multi-tenant data separation
- [ ] Transactions (ACID, commit/rollback) — Approval + audit atomicity
- [ ] Connection pooling — Concurrent gateway requests

## 5. Containerization & Deployment

- [ ] Docker (images, Dockerfile, layers, volumes) — Package gateway, OPA, Postgres
- [ ] Docker Compose (services, networks, healthchecks) — Multi-service local stack
- [ ] Environment variables (secrets, config) — DATABASE_URL, OPA_URL, SECRET_KEY
- [ ] Health checks (readiness/liveness) — Service startup ordering
- [ ] Self-hosting (one-command deploy) — MVP acceptance: `docker compose up`

## 6. CI/CD (GitHub Actions)

- [ ] GitHub Actions (workflows, jobs, steps, secrets) — Automated testing on push/PR
- [ ] pytest (fixtures, parametrize, asyncio) — Gateway unit/integration tests
- [ ] Test coverage (pytest-cov) — 80% coverage gate
- [ ] Linting (ruff) — Code quality enforcement
- [ ] Dependency scanning (pip-audit, safety) — Cross-cutting security

## 7. Security Concepts (Core Differentiator)

- [ ] JWT (JSON Web Tokens: header, payload, signature) — Agent short-lived tokens
- [ ] OAuth2 / OIDC (authorization code, PKCE, JWKS) — Keycloak identity, agent auth
- [ ] Encryption at rest (envelope encryption, AES-256) — Secrets store, Vault
- [ ] Digital signatures (Ed25519, HMAC) — Audit log signed roots
- [ ] Hash chains (append-only audit, tamper detection) — audit_events immutability
- [ ] SSRF protection (allowlists, private IP blocking) — HTTP connector security
- [ ] Tenant isolation (row-level security, scoped queries) — Multi-tenant data separation
- [ ] Default deny / fail closed — Policy engine behavior
- [ ] Delegation chains (human → agent → session) — Accountability for every action
- [ ] Rate limiting & per-agent budgets — DoS prevention
- [ ] Secrets scanning (detecting leaked keys in CI) — Cross-cutting security
- [ ] Confused deputy prevention — Scope validation per call

## 8. Policy Engine (OPA + Rego)

- [ ] Rego language (rules, functions, input/data) — Writing allow/deny policies
- [ ] OPA sidecar architecture (REST API, /v1/data) — Policy decision service
- [ ] Policy input schema (who/what/on_what/context) — Contract between gateway and OPA
- [ ] Policy versions (stored in Postgres) — Auditability of policy changes
- [ ] Dry-run / simulate mode — Testing policies without side effects
- [ ] Deny reasons & obligations — User-friendly API responses

## 9. Model Context Protocol (MCP)

- [ ] MCP architecture (client, server, host) — Agent-tool communication
- [ ] MCP JSON-RPC (initialize, tools/list, tools/call) — Gateway MCP proxy
- [ ] MCP proxy/gateway (session management, namespacing) — Route MCP through gateway
- [ ] MCP tool discovery with policy enforcement — Gate which tools agents can call
- [ ] @playwright/mcp (browser automation) — Browser automation connector
- [ ] MCP credentials (agents never see raw secrets) — Credential brokering

## 10. AI Agents & Orchestration

- [ ] LLM basics (prompt, completion, tokens, temperature) — Agent reasoning
- [ ] Tool use / function calling (LLM → tool → result) — Agent actions
- [ ] Agent orchestration (graphs, state, handoffs, retries) — LangGraph workflows
- [ ] Human-in-the-loop (pause, approve, resume) — Approvals phase
- [ ] Durable execution (checkpoints, resume after failure) — Long-running workflows
- [ ] Multi-agent patterns (sequential, concurrent, handoff) — Cross-step policies
- [ ] Prompt injection (attacks & defenses) — Red-team phase

## 11. Audit & Observability

- [ ] Structured logging (JSON logs) — Gateway observability
- [ ] Distributed tracing (traces, spans, context propagation) — OpenTelemetry
- [ ] Metrics (counters, histograms, gauges) — Cost, performance, budgets
- [ ] Hash-chained audit log (immutability verification) — Tamper detection
- [ ] Verification CLI (recompute hashes, detect tampering) — Audit acceptance criteria

## 12. Frontend (Next.js + TypeScript)

- [ ] React (components, hooks, state, effects) — Console UI
- [ ] Next.js App Router (server/client components, routing) — Console pages
- [ ] Tailwind CSS (utility-first styling) — Console styling
- [ ] API consumption (fetch, SWR, React Query) — Console calling gateway
- [ ] Authentication in frontend (token storage, refresh) — Console login/session

## 13. Linux & CLI

- [ ] Bash (navigation, permissions, processes, pipes) — Daily development
- [ ] SSH (remote access, key-based auth) — Deployment, servers
- [ ] curl / HTTPie (testing APIs manually) — Debugging gateway
- [ ] jq (JSON processing in CLI) — Inspecting API responses

## 14. Business / Product Concepts

- [ ] B2B SaaS (subscription, usage-based, tiers) — Business model
- [ ] Customer discovery (interviews, problem validation) — Finding first design partners
- [ ] MVP (minimum viable product, one complete outcome) — Scope discipline
- [ ] Go-to-market (design partners, pilots, channel partners) — Getting first customers
- [ ] Legal (Algerian startup status, incubator terms, IP) — Founder protection

## Suggested Learning Order (First 4 Weeks)

**Week 1:** Python basics → FastAPI → PostgreSQL → Docker
**Week 2:** HTTP/JSON → JWT → Git/GitHub Actions → pytest
**Week 3:** OPA/Rego → MCP basics → TypeScript/React basics
**Week 4:** LangGraph basics → Security concepts (SSRF, tenant isolation, hash chains) → Start building Phase 1

## How to Use This List

- Check off each concept as you understand it **AND** use it in code
- Learn just-in-time for each phase — don't learn everything before coding
- Pair programming: one person reads docs, other writes code, switch roles
- Build a "hello world" for each new technology before using it in the project
