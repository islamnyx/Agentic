# Architecture — Observability

Unified cross-provider observability: one audit trail and metrics view for agent activity regardless of which framework built the agent.

## Components

- Hash-chained tamper-evident audit log with Ed25519-signed roots
- Verify CLI to detect tampering
- External hash anchoring (append-only anchor log)
- OpenTelemetry tracing and metrics (logs, traces, costs)
- Business metrics tables: dashboard_metrics, security_incidents, agent_costs

## Design principle

Observability is provider-agnostic. A company using Gemini, Claude, and n8n sees one unified audit trail, not three separate logs.

## Links

- Parent: [[modules]]
- Strategy: [[../../../../planning/architecture/modules]]
