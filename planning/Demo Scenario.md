# Demo Scenario — Finance/Ops Agent

## Agent Role

Finance/ops agent with four capabilities:

| Tool | Description | Risk |
|------|-------------|------|
| read_invoices | Read invoice records from DB | Low — read-only, tenant-scoped |
| query_db | Run parameterized read-only SQL queries | Medium — arbitrary SQL surface |
| email_customers | Send email to customers via SMTP | High — outbound communication |
| issue_refunds | Issue refunds to customers | Critical — moves money |

## Flow

1. Agent registers with gateway, receives short-lived scoped token
2. Agent calls `read_invoices` — gateway checks policy, allow, logs
3. Agent calls `query_db` — gateway checks policy, allow, logs
4. Agent calls `email_customers` — policy returns `require_approval`, parks in queue
5. Human approver reviews in console, approves/denies
6. Agent calls `issue_refunds` above threshold — `require_approval`, bound to exact params hash

## Assumptions

- Agent is operated by a finance/ops user within an organization
- Refunds above $500 require human approval
- Emails to customers require human approval
- All actions are tenant-scoped
