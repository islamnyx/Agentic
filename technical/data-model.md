# Data Model

Core tables: organizations, users, agents, departments, teams, agent_tokens, tools, connectors, secrets, policies (versioned), policy_bindings, sessions, delegation_chains, tool_calls, decisions, approvals, audit_events, secret_leases, billing, usage, knowledge_items, knowledge_access, dashboard_metrics, security_incidents, agent_costs.

- **audit_events** is append-only. Each row stores the hash of the previous row plus its own content (prev_hash, hash), plus Ed25519 signature on periodic signed roots. A verification command/CLI detects tampering.
- **delegation_chains** records human → agent → session authorization with scope/justification; required on tool_calls, approvals, decisions, audit_events.
- **secret_leases** tracks short-lived brokered credentials; secrets encrypted at rest (envelope encryption, Postgres + Vault/KMS).
- **approvals** bound to params hash and full delegation chain context.
- **knowledge_items** store company documents, procedures, products, pricing, customer info, business rules; **knowledge_access** grants per-item read/write permissions scoped to department/team/agent.
- **dashboard_metrics** aggregate work completed, revenue/cost, pending approvals, failed tasks, agent costs; **security_incidents** and **agent_costs** feed the Control Center.
- Fast revocation via agent_tokens revocation lists and agents.revoked_at.

## Links

- Supports: [[request-flow]]
- Implemented in: [[phases/phase-1]], [[phases/phase-2]], [[phases/phase-4]], [[phases/phase-5]]
