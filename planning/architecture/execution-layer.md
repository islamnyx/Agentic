# Architecture — Execution Layer

The enforcement layer: runs the Secure Execution Gateway that intercepts tool calls before they reach business systems.

## Components

- Agent registration from any supported framework (Gemini, Claude, OpenAI, n8n, custom, MCP)
- Secure Execution Gateway — policy-enforced interception of tool calls
- Credential brokering (short-lived, scoped; agents never receive real secrets)
- Policy evaluation before sensitive actions (OPA)

## Design principle

Security is enforced outside the language model. The LLM only proposes actions; the Eclipse gateway decides whether to allow them. Agents hold only short-lived tokens; real secrets are brokered by the gateway. Agents cannot bypass enforcement with direct credentials or alternative integrations.

## Links

- Parent: [[Index]]
- Control plane: [[control-plane]]
- Modules: [[modules]]
