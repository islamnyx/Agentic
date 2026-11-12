# Architecture — Departments & Teams

Agents are organized into departments and teams, not treated as isolated chatbots. Each department has a manager agent that coordinates the work, plus specialist agents (e.g. Lead Research, CRM, Sales, Reporting).

## Components

- **departments** — department records (name, owner organization, manager agent)
- **teams** — team records within a department
- **department_agents** — agents assigned to a department/team with scoped identity
- **Agent OS Security Layer** — Identity · Permissions · Approval · Audit · Monitoring wrapping every department
- **Department-scoped policy** — cross-department agent calls require explicit policy approval

## Design principle

The LLM only proposes actions; the gateway decides. Department boundaries are enforced by policy, not by agent prompts.

## Links

- Parent: [[modules]]
- Strategy: [[../../../../planning/product/capabilities]]
- Data model: [[../../data-model]]
