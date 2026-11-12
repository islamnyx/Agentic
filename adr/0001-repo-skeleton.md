# ADR 0001 — Repository and CI Skeleton

## Status

Accepted

## Context

Phase 0 requires a runnable repo with docker-compose and CI before any
gateway code exists. The stack is defined in `technical/Stack.md`.

## Decision

- Python 3.12 + FastAPI + Pydantic for the gateway
- PostgreSQL 16 for registry, policies, audit, approvals
- OPA sidecar for policy decisions
- Docker Compose for local dev; GitHub Actions for CI
- pytest for testing, ruff for lint/format

## Consequences

- Single-repo monorepo layout (gateway + infra configs)
- CI runs pytest against ephemeral Postgres service container
- `docker compose up` brings up full local stack
