# Threat Model Draft — Phase 0

## Scope

Governance gateway for business AI agents. The gateway sits between agents and
business systems (invoices, DB, email, refunds). Every agent action flows
through the gateway; agents never hold real credentials.

## Threats

| ID | Threat | Asset | Impact | Mitigation |
|----|--------|-------|--------|------------|
| T01 | Token theft — agent JWT stolen or intercepted | agent_tokens | Attacker impersonates agent, makes unauthorized calls | Short-lived signed tokens, rotation, revocation, HTTPS-only, token binding |
| T02 | Policy tampering — Rego rules modified to allow forbidden actions | policies table | Unauthorized actions permitted | Policy changes audited and approval-gated, versioned policies, signed policy roots |
| T03 | Audit tampering — audit_events edited or deleted | audit_events | Cover-up of malicious activity | Hash-chained append-only log, signed roots, verification CLI detects tampering |
| T04 | Confused deputy — agent tricks gateway into acting with excessive privilege | delegation_chains | Agent performs action outside its scope | Delegation chain validation per call, scope enforcement, least-privilege tokens |
| T05 | SSRF — HTTP connector reaches internal/private IPs | HTTP connector | Data exfiltration, internal network scanning | Allowlist of destinations, no private IP ranges, no redirects by default |
| T06 | Tenant isolation failure — org A reads org B's data | organizations, agents | Cross-tenant data leak | Tenant-scoped queries, tenant isolation tests from start, row-level security |
| T07 | Credential exposure — agent receives real secrets | secrets, secret_leases | Full compromise of business systems | Credential brokering: agents hold gateway token only, real secrets brokered short-lived |
| T08 | Denial of service — runaway agent floods gateway | gateway service | Service unavailability | Rate limiting, per-agent budgets, request timeouts |

## Trust Boundaries

- Agent <-> Gateway: authenticated via short-lived signed token
- Gateway <-> OPA: internal, trusted
- Gateway <-> Postgres: internal, trusted
- Gateway <-> Business systems: brokered credentials, allowlisted destinations

## Assumptions

- OPA sidecar is deployed alongside gateway and treated as trusted
- PostgreSQL is the source of truth for policies, agents, audit
- Human approvers are out-of-band (console + webhook)

## Next Steps

- Review threat model with whole team
- Map each threat to a test in CI
- Revisit before each phase gate
