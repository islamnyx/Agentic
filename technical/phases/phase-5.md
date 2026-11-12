# Phase 5 - Audit (Complete)

Implemented:
- Hash-chained audit log (prev_hash, hash per row) — `gateway/models/audit_entry.py`, `gateway/core/audit.py`
- Ed25519 signature on periodic signed roots — `AuditService.sign_root()`, `/v1/audit/sign-root`
- Verify CLI (detects tampering) — `gateway/cli/verify_audit.py`, `/v1/audit/verify`
- Export to JSON — `AuditService.export_json()`, `/v1/audit/export`
- Optional external hash anchoring — `AnchorService`, `/v1/audit/anchor-root`, `--anchor`/`--verify-anchors` CLI flags
- Business metrics tables (dashboard_metrics, security_incidents, agent_costs) — migration `0008_business_metrics.py`, `gateway/models/metrics.py`, `gateway/api/v1/metrics.py`
- MCP audit integration — MCP proxy writes hash-chained AuditEntry logs for every MCP call
- OpenTelemetry integration — `gateway/core/observability.py`, tracing + metrics middleware in `gateway/main.py`

Done when: editing a DB row detected by verification. (Verified by tests.)

Tests: `tests/test_phase5.py` — 13 passing (hash chain, tamper detection, deletion detection, export, signing, anchoring, metrics models, observability, anchor API).

## Links

- Prev: [[phase-4]]
- Next: [[phase-6]]
