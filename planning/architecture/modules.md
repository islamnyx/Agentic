# Architecture — Modules

| Module | Responsibility |
|--------|---------------|
| Agent Registry | Discover and register agents from any supported framework |
| Agent Identity & Access | Scoped identity, credentials, short-lived tokens; agents never receive real secrets |
| Secure Execution Gateway | Intercept tool calls; allow / deny / require_approval; enforce before business systems |
| Unified Audit & Monitoring | Hash-chained tamper-evident audit trail; signed roots; verify CLI; business metrics |
| Integration SDK | SDK + APIs to connect existing agents to Eclipse |
| Security Engine | Identity, permissions, OPA policies, approvals, secrets (envelope encryption), audit |
| Integration Hub | Reusable connectors (HTTP, PostgreSQL, SMTP, MCP) routed through the Secure Execution Gateway |
| Company Brain | Shared knowledge base with per-item access permissions (deprioritized vs. governance) |
| Departments & Teams | Agent organization into departments; cross-department access governed by policy |
| Approvals Platform | Human-in-the-loop approval bound to exact action + parameters |
| Business Dashboards | Business outcomes: work completed, revenue/cost, pending approvals, failures, security incidents, agent costs |
| Deployment | Cloud, customer-controlled, private; Docker Compose, self-hostable from day one |

## Business systems governed

CRM · ERP · Databases · Email · WhatsApp Business · Internal APIs · Documents

## Design principle

Eclipse is the enforcement point. Protected actions pass through the Secure Execution Gateway; agents cannot bypass it with direct credentials.

## Links

- Parent: [[Index]]
- Control plane: [[control-plane]]
- Execution layer: [[execution-layer]]
