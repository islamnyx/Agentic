# Architecture — Control Plane

Central management layer: Organizations, Users, Agents, Departments & Teams, Policies, Integrations, Company Brain, Billing.

## Design principle

Modular monolith, not microservices. Keep control plane and runtime conceptually separated, avoid unnecessary infrastructure. Everything runs from Docker Compose, self-hostable from day one.

## Components

- **Organizations** — multi-tenant isolation
- **Users** — human operators and administrators
- **Agents** — registered AI agents with scoped identities
- **Departments & Teams** — agents organized into departments (manager + specialist agents)
- **Policies** — versioned policy rules governing agent actions
- **Integrations** — connectors to business systems
- **Company Brain** — shared knowledge base; every knowledge item carries access permissions enforced outside the LLM
- **Billing** — subscription and usage tracking

## Do not force

Do not force all agents to use your own runtime. Let customers bring agents built with supported frameworks and connect them through your security and integration layer.

## Links

- Parent: [[Index]]
- Execution layer: [[execution-layer]]
- Strategy: [[../../planning/architecture/control-plane]]
