# MVP Acceptance Criteria

- Agent registered, scoped identity with full delegation chain (human → agent → session), revoked in seconds.
- No tool call reaches a business system without a logged policy decision.
- Agents never receive real credentials; all secrets brokered via gateway with envelope encryption.
- MCP tool calls governed with same policy enforcement as native connectors.
- High-risk actions pause for a human; approval bound to exact parameters and visible with full context (Slack/console).
- Audit log uses hash-chained entries with signed roots; verification CLI/tool detects tampering.
- Delegation chain provably recorded for every action (who authorized what).
- Demo prompt-injection attack blocked, report shows why with full audit trail.
- Deploys with one command on customer's own machine.
- Company Brain knowledge item access enforced by per-item ACLs (sales agent cannot read HR/finance items).
- Department-scoped agent registration enforced; cross-department calls require policy approval.
- Business dashboard shows work completed, pending approvals, failed tasks, security incidents, and agent costs.

## Links

- Validated by: [[phases/phase-8]]
- Required by: [[../../planning/go-to-market/phases]]
