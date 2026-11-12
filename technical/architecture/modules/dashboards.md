# Architecture — Business Outcome Dashboards

Dashboards show business owners business results, not just technical logs.

## Metrics

- Work completed by agents
- Money saved or revenue generated, where measurable
- Pending approvals
- Failed tasks
- Security incidents
- Agent costs

## Components

- **dashboard_metrics** — aggregated business metrics per organization/department
- **security_incidents** — recorded security events feed the Control Center
- **agent_costs** — per-agent and per-department cost tracking
- **Control Center pages** — approvals, monitoring, costs, security view for IT/security teams

## Design principle

Business owners need to understand business outcomes. Metrics are computed from audit_events, approvals, tool_calls, and agent_costs, not from LLM logs.

## Links

- Parent: [[modules]]
- Strategy: [[../../../../planning/product/capabilities]]
- Observability: [[observability]]
