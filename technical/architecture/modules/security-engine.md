# Architecture — Security Engine

Core differentiator. Security enforced outside the language model.

## Components

- Agent identity and authentication
- Tool-level and action-level permissions
- Resource-level access restrictions
- Policy evaluation before sensitive actions (OPA)
- Human approval for high-risk operations
- Secrets management (envelope encryption; agents never receive real credentials)
- Immutable / tamper-evident audit records (hash-chained)
- Emergency agent revocation
- Multi-provider agent registration and scoped identities

## Design principle

Never rely on an agent's prompt to enforce access control. Default deny, fail closed. Eclipse is the enforcement point — protected actions pass through the Secure Execution Gateway and cannot be bypassed with direct credentials.

## Links

- Parent: [[modules]]
- Details: [[../../security-engine]]
- Strategy: [[../../../../planning/architecture/modules]]
