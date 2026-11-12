# Phases — Implementation

Eclipse Agent OS is an independent Agent Control Plane. Phases are organized around governance (registry, identity, execution gateway, audit, SDK), not agent creation.

| Phase | Weeks | Focus |
|-------|-------|-------|
| Phase 0 | 1-2 | Foundations: repo, CI, compose, threat model, policy schema, coding standards |
| Phase 1 | 3-5 | Gateway skeleton: agent registry, signed tokens, tool registry, invoke endpoint; departments & Company Brain schema |
| Phase 2 | 6-8 | Policy engine: OPA sidecar, Rego policies, department-scoped and knowledge ACL policies |
| Phase 3 | 9-10 | Connectors: HTTP, PostgreSQL, SMTP, MCP proxy, secrets store; Company Brain ingestion + ACL-enforced knowledge query |
| Phase 4 | 11-12 | Approvals: reusable platform, bound to exact params, expiry, single-use, kill switch |
| Phase 5 | 13-14 | Audit: hash-chained log, verify CLI, export, external anchoring, business metrics, MCP audit, OpenTelemetry |
| Phase 6 | 15-16 | Cross-step policies: trust labels, session-aware rules |
| Phase 7 | 17-18 | Console: Control Center (identities, permissions, knowledge, approvals, monitoring, costs, security). Agent Studio deferred. |
| Phase 8 | 19-20 | Red-team & hardening: prompt-injection suite, pen-test, docs, demo |

## Done when (Phase 0)

Repo runs `docker compose up` and threat model reviewed by everyone.

## Strategic note

Eclipse does not compete to be another place to build agents (Google AI Studio, Claude Cowork already do this). Eclipse is the independent control plane that governs agents regardless of where they were built. Agent Studio and advanced orchestration are deferred to post-MVP.

## Links

- Parent: [[Index]]
- Business phases: [[../../planning/go-to-market/phases]]
