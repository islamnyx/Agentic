# ADR 0002 — Microsoft Agent Governance Toolkit reviewed as alternative policy engine

## Status

Considered / Reference — not adopted as the primary engine. OPA remains the Phase 2 policy engine; AGT is retained as a documented sub-ms alternative for latency-sensitive deployments.

## Context

Phase 2 (Policy Engine) integrated Open Policy Agent (OPA) as the policy decision point, evaluated over the normalized `who/what/on_what/context` input through `gateway/core/opa.py`. OPA runs as a sidecar (`docker-compose.yml:20`) and is called over HTTP per tool invocation.

The todo list's final Phase 2 item is a review of the **Microsoft Agent Governance Toolkit (AGT)** as an "alternative/reference — sub-ms policy engine". AGT (github.com/microsoft/agent-governance-toolkit, MIT) is an open-source runtime governance toolkit for AI agents covering all 10 OWASP Agentic AI Top 10 risks.

Key AGT facts from upstream (README + Microsoft Open Source blog, 2026-04-02):
- **Agent OS** policy engine: stateless, deterministic, fail-closed, intercepts every agent action before execution.
- Latency: sub-millisecond, <0.1ms p99 (OPA sidecar HTTP call is network-bound and higher).
- Policy languages: YAML/JSON rules, OPA Rego, AWS Cedar.
- Python package: `agent-governance-toolkit` (PyPI), Python 3.10+; consolidated core distro `agent-governance-toolkit-core`.
- Two host APIs documented in README:
  - `from agentmesh.governance import govern` → `safe_tool = govern(my_tool, policy="policy.yaml")`, raises `GovernanceDenied` on block.
  - `from agent_control_specification import AgentControl` → `runtime.evaluate("input", {...})`, returns `result.verdict`; `runtime.close()`.
- CLI: `agt doctor`, `agt verify` (OWASP), `agt lint-policy`, `agt red-team scan`.
- 992 conformance tests across 10 formal specs; 29 ADRs; SLSA-compatible builds; OpenSSF Scorecard; CodeQL/Dependabot.
- Covers OWASP Agentic AI Top 10 (all 10), NIST AI RMF, EU AI Act, SOC 2, AARM Extended.
- Framework adapters: LangChain, CrewAI, LangGraph, AutoGen, Semantic Kernel, Google ADK, Microsoft Agent Framework, OpenAI Agents SDK, Haystack, MCP, Dify, Azure AI Foundry.

## Decision

Keep OPA as the primary Phase 2 engine. Do **not** replace OPA with AGT today, because:
- OPA is already wired end-to-end (sidecar, Rego policies, invoke integration, policy_versions, tests).
- The gateway's normalized `who/what/on_what/context` schema maps cleanly to OPA Rego and is already tested.

Adopt AGT as a **documented reference/alternative** policy engine for sub-ms latency requirements. Add a thin reference wrapper (`gateway/core/agt_policy.py`) implementing the same `evaluate_policy(input_doc) -> PolicyDecision` interface as `gateway/core/opa.py`, backed by AGT's `AgentControl` ACS host API, with fail-closed semantics and dry-run parity. This lets operators swap the decision point by config without rewriting the invoke layer.

AGT policy input shape (per ACS `runtime.evaluate("input", {...})`):
```
{
  "envelope": {"agent_id": "<id>"},
  "input": {"body": {"action": "...", "params": {...}}}
}
```
AGT returns a verdict object with `.verdict` (allow/deny/require_approval) plus reasons.

## Consequences

### Positive
- Sub-ms (<0.1ms p99) local policy evaluation vs OPA sidecar HTTP round-trip, for latency-sensitive paths.
- Single YAML policy file usable across Python/TypeScript/.NET/Rust/Go SDKs (polyglot teams).
- Built-in OWASP/NIST/EU AI Act/SOC2 compliance mapping and `agt verify`/`agt lint-policy` CLI.
- Fail-closed by default; denials are structurally enforced, not probabilistic.

### Negative / Risks
- AGT is public preview (may have breaking changes before GA).
- `agent-governance-toolkit` wheel was not resolvable in this sandboxed env; integration is reference-quality (mocked in tests) until the package is available in production builds.
- Adds a second policy engine to operate and version alongside OPA and `policy_versions` table.
- AGT policy language (YAML/ACS) differs from the gateway's Rego policies; rules would need to be ported, not shared directly.

### Mitigations
- Reference wrapper mirrors `PolicyDecision` interface so OPA and AGT are interchangeable at the invoke layer.
- Dry-run mode (`POLICY_DRY_RUN`) applies equally to AGT-backed decisions.
- All AGT-backed decisions are logged to `ToolCall.decision` / `decision_reason` identical to OPA.

## Review summary (AGT vs OPA)

| Dimension | OPA (adopted) | AGT (reference alt) |
|---|---|---|
| Decision latency | HTTP sidecar round-trip | <0.1ms p99 in-process |
| Policy language | Rego | YAML, Rego, Cedar |
| Deployment | Sidecar container | In-process / sidecar |
| Fail-closed | Yes (gateway denies when OPA unreachable) | Yes (wrapper denies on exception) |
| Compliance mapping | Custom | OWASP/NIST/EU AI Act/SOC2 built-in |
| CLI audit tooling | None built-in | `agt verify`, `agt lint-policy`, `agt red-team scan` |
| Test coverage | Phase 2 unit tests | 992 conformance tests upstream |
| Integration status | Wired + tested | Reference wrapper + mocked tests |

## Related

- `gateway/core/opa.py` — primary OPA client
- `gateway/core/agt_policy.py` — AGT reference wrapper
- `gateway/schemas/policy-input.json` — normalized policy input
- `technical/todo.md` — Phase 2 Policy Engine (last item)
