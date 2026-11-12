# Security Engine

Core differentiator of Agent OS. Cybersecurity expertise influences the entire platform architecture.

## Threats

| ID | Threat | Asset | Mitigation |
|----|--------|-------|------------|
| T01 | Token theft | agent_tokens | Short-lived signed tokens, rotation, revocation, HTTPS-only |
| T02 | Policy tampering | policies | Versioned policies, approval-gated changes, signed roots |
| T03 | Audit tampering | audit_events | Hash-chained append-only log, verification CLI |
| T04 | Confused deputy | delegation_chains | Delegation chain validation per call, scope enforcement |
| T05 | SSRF | HTTP connector | Allowlist, no private IP ranges, no redirects by default |
| T06 | Tenant isolation failure | organizations | Tenant-scoped queries, row-level security |
| T07 | Credential exposure | secrets | Credential brokering; agents hold gateway token only |
| T08 | Denial of service | gateway service | Rate limiting, per-agent budgets |
| T09 | Knowledge over-read | knowledge_items | Per-item ACLs (knowledge_access); sales agent cannot read HR/finance items |
| T10 | Department isolation failure | departments | Department-scoped agent registration; cross-department calls policy-enforced |

## Cross-cutting

- Rate limiting and per-agent budgets
- Strict input validation on every connector
- Tenant isolation tests from start
- Dependency pinning and scanning, secrets scanning in CI
- Policy changes audited and approval-gated

## Links

- Origin: [[phases/phase-0]]
- Protects: [[request-flow]]
- Module: [[architecture/modules/security-engine]]
