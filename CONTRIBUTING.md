# Coding Standards

## Language

- Python 3.12+ for gateway and agent SDK
- TypeScript for Next.js console
- No `any` in TypeScript; strict mode enabled

## Python

- Ruff for linting and formatting (line-length 100)
- Pydantic v2 models for all request/response validation
- Async/await throughout; no blocking I/O in request path
- Type hints on all public functions
- Docstrings on modules and public classes/functions (Google style)
- Structured logging via `logging` with JSON output; no `print()`

## Testing

- pytest with pytest-asyncio
- One test file per module: `tests/test_<module>.py`
- 80%+ coverage gate in CI
- Every new feature needs unit tests; every bug fix needs a regression test

## Database

- SQLAlchemy 2.0 async ORM
- Alembic migrations; every schema change needs a migration
- No raw SQL except parameterized queries via SQLAlchemy text()

## Security

- Secrets never logged; never in source control
- All user input validated via Pydantic before reaching business logic
- Default deny: missing policy = deny
- Tenant ID included in every query; cross-tenant access prohibited

## Git

- Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`)
- PRs require review before merge to `main`
- ADR required for architectural decisions

## Frontend

- Next.js App Router, TypeScript strict
- Tailwind CSS for styling
- Server components by default; client components only for interactivity
