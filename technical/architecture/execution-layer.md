# Architecture — Execution Layer

Runs agents, executes workflows, calls approved tools, enforces policies.

## Design principle

Security enforced outside the language model. The LLM only proposes actions; the gateway decides whether to allow them. Agents hold only short-lived tokens; real secrets are brokered by the gateway.

## Links

- Parent: [[Index]]
- Control plane: [[control-plane]]
- Strategy: [[../../planning/architecture/execution-layer]]
