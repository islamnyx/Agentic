# Product — MVP

## Revised MVP: Eclipse Agent OS — Independent Control Plane

The MVP is not a place to build agents. It is a narrow, focused control plane that governs agents regardless of where they were built.

Build first (narrow, sellable):

1. **Agent Registry** — Discover and register agents from supported frameworks.
2. **Agent Identity and Access** — Distinct identity, credentials, and permissions for every registered agent.
3. **Secure Execution Gateway** — Control tool calls to protected business systems. Allow, deny, or request approval.
4. **Unified Audit and Monitoring** — Show what every supported agent did, which policies applied, and what happened.
5. **Integration SDK** — A straightforward way for developers to connect their existing agents.

Build later (once customers demonstrate need):

- Visual Agent Studio
- Advanced orchestration
- Company Brain as a knowledge repository (deprioritized vs. governance)

## MVP capabilities

| Capability | Description |
|------------|-------------|
| Agent Registry | Register agents from Gemini, Claude, OpenAI, n8n, custom Python, and MCP |
| Agent Identity & Access | Scoped identity and credentials; short-lived tokens; agents never receive real secrets |
| Secure Execution Gateway | Policy-enforced interception of tool calls; allow / deny / require_approval |
| Unified Audit | Hash-chained, tamper-evident audit trail across all providers; verify CLI |
| Integration SDK | SDK + APIs to connect existing agents to the Eclipse control plane |

## What we intentionally do NOT build in MVP

- Visual Agent Studio (deferred — not the differentiator)
- Agent orchestration engine (deferred — customers already have n8n/LangGraph/etc.)
- Company Brain as a primary knowledge product (deprioritized)

## Links

- Parent: [[Index]]
- Architecture: [[../architecture/control-plane]], [[../architecture/execution-layer]]
- Technical criteria: [[../../technical/mvp-criteria]]
