# Architecture — Approvals Platform

Human approval is a reusable platform capability, not a one-off step. The security engine binds approval to the exact action and its parameters, expires approvals, prevents reuse, and records who approved it.

## Components

- **approvals** — pending/approved/denied state, bound to params hash + full delegation chain context
- **Approver queue** — human approvers review and approve/deny with timeout
- **Approval hooks** — pre-tool-call gating via MCP gateway and policy engine (OPA require_approval decisions)
- **Expiry & single-use** — approvals expire and cannot be reused after the bound parameters change
- **Notification** — Slack/Teams webhooks with full context for approvers

## Examples

- Approve a payment
- Approve a discount
- Approve an email campaign
- Approve a customer record deletion

## Design principle

Never rely on the agent to self-approve. Approval is decided by the gateway, bound to exact parameters, and immutably audited.

## Links

- Parent: [[modules]]
- Strategy: [[../../../../planning/product/capabilities]]
- Phases: [[../../phases/phase-4]]
- Data model: [[../../data-model]]
