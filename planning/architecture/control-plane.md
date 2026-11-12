# Architecture — Control Plane

The central management layer of Eclipse Agent OS: the independent control plane that governs agents from any provider.

## Components

- **Organizations** — multi-tenant isolation
- **Users** — human operators and administrators (CTO, IT, security)
- **Agents** — registered agents from any framework with scoped identities
- **Departments & Teams** — agents organized into departments; cross-department access governed by policy
- **Policies** — versioned policy rules governing agent actions across all providers
- **Integrations** — connectors to business systems, routed through the Secure Execution Gateway
- **Company Brain** — shared knowledge base; per-item access permissions (deprioritized vs. governance)
- **Billing** — subscription and usage tracking

## Design principle

Modular monolith, not microservices. Everything runs from Docker Compose, self-hostable from day one.

## Do not force

Do not force all agents to use your own runtime. Let customers bring agents built with supported frameworks and connect them through Eclipse security and integration. Eclipse does not own the model or framework — it governs how agents interact with the business.

## Links

- Parent: [[Index]]
- Execution layer: [[execution-layer]]
- Modules: [[modules]]
