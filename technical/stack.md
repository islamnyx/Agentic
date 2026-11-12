# Technology Stack

| Component          | Choice                                    | Why                                                            |
| ------------------ | ----------------------------------------- | -------------------------------------------------------------- |
| Frontend           | Next.js + TypeScript                      | Console for agents, approvals, audit                           |
| Backend            | Python 3.12 + FastAPI + Pydantic          | Fast to build, strong typing                                   |
| Database           | PostgreSQL                                | Registry, policies, audit, approval queue                      |
| Background jobs    | Redis + Celery                            | Workflow orchestration and retries                             |
| Policy engine      | Open Policy Agent (OPA) sidecar over REST | Standard, testable policy-as-code                              |
| Workflow engine    | LangGraph or n8n                          | Established engine, not built from scratch                     |
| Authentication     | OIDC; Keycloak or managed provider        | Identity                                                       |
| Secrets            | Vault or cloud secret manager             | Envelope encryption                                            |
| Observability      | OpenTelemetry                             | Logs, traces and costs                                         |
| Deployment         | Docker                                    | Self-hostable from day one                                     |
| Browser automation | Playwright MCP (@playwright/mcp)          | MCP-first browser automation, routed through gateway MCP proxy |

Skip for now: multi-region, marketplace, billing engine, visual builder (MVP uses SDK + API-first).

## Links

- Parent: [[Index]]
- Runs: [[request-flow]]
- Stores: [[data-model]]
