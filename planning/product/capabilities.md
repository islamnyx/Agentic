# Product — Capabilities

## 1. Multi-provider governance

One control plane for Gemini, Claude, OpenAI, n8n, and custom agents. Eclipse does not require customers to rebuild agents on its platform. Agents are discovered, registered, and governed where they already run.

## 2. Business-wide permissions

Policies based on employee, agent, department, resource, and action. A single policy set applies across every supported agent framework — sales agents cannot access HR data regardless of whether they run on Claude or Gemini.

## 3. Independent execution enforcement

Eclipse intercepts and authorizes sensitive tool calls before they reach business systems. Allow, deny, or request approval. Agents cannot bypass enforcement with direct credentials or alternative integrations.

## 4. Unified agent observability

One audit trail for agent activity across supported providers. Hash-chained, tamper-evident records with signed roots and a verification CLI.

## 5. Deployment flexibility

Cloud, customer-controlled infrastructure, and private deployments. Eclipse runs from Docker Compose, self-hostable from day one.

## Supporting capabilities (post-MVP)

These exist to support the five differentiators above, not as standalone products:

- **Agent Studio (deferred):** Visual builder for agent creation. Not the differentiator; build only if customers ask.
- **Orchestration (deferred):** Coordinate agent workflows. Customers already use n8n, LangGraph, CrewAI.
- **Integration Hub:** Connectors to business systems (HTTP, PostgreSQL, SMTP, Playwright MCP). Routes through the Secure Execution Gateway.
- **Company Brain:** Shared knowledge layer with per-item ACLs. Deprioritized vs. governance.
- **Approvals Platform:** Reusable human-in-the-loop approval bound to exact action + parameters.
- **Business Dashboards:** Business outcomes — work completed, pending approvals, failed tasks, security incidents, agent costs.

## Links

- Parent: [[mvp]]
- Architecture: [[../architecture/modules]]
- Experiences: [[agent-os-experiences]]
