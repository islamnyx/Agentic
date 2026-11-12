"""PostgreSQL connector: read-only default, parameterized queries only (Phase 3)."""

from __future__ import annotations

from typing import Any

try:
    import asyncpg
except Exception:  # pragma: no cover - asyncpg optional in test environments
    asyncpg = None  # type: ignore[assignment]

from gateway.connectors.base import (
    ConnectorBase,
    ConnectorError,
    has_parameter_placeholders,
    is_read_only_select,
)


class PostgresConnector(ConnectorBase):
    """Read-only PostgreSQL connector.

    Config keys:
      host, port, dbname, user: connection parameters (host/port/dbname/user)
      sslmode: "disable" (default), "require"

    The ``secret`` injected by the broker is used as the password. Only a
    single SELECT statement with parameter placeholders is permitted.
    """

    connector_type = "postgres"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.host = self.config.get("host", "localhost")
        self.port = int(self.config.get("port", 5432))
        self.dbname = self.config.get("dbname", "postgres")
        self.user = self.config.get("user", "postgres")
        self.sslmode = self.config.get("sslmode", "disable")

    def validate_params(self, params: dict[str, Any]) -> None:
        query = params.get("query")
        if not query or not isinstance(query, str):
            raise ConnectorError("PostgreSQL connector requires a 'query' parameter")
        if not is_read_only_select(query):
            raise ConnectorError("Only a single read-only SELECT statement is allowed")
        if not has_parameter_placeholders(query):
            raise ConnectorError("Query must use parameter placeholders ($1, $2, ...)")
        parameters = params.get("parameters")
        if parameters is not None and not isinstance(parameters, (list, tuple)):
            raise ConnectorError("'parameters' must be a list")

    async def _run(
        self, params: dict[str, Any], secret: str | None = None
    ) -> dict[str, Any]:
        if asyncpg is None:
            raise ConnectorError("asyncpg is not installed")
        query = params["query"]
        parameters = params.get("parameters") or []
        conn = None
        try:
            conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                database=self.dbname,
                user=self.user,
                password=secret,
                ssl=self.sslmode if self.sslmode != "disable" else None,
            )
            rows = await conn.fetch(query, *parameters)
            return {
                "rows": [dict(r) for r in rows],
                "row_count": len(rows),
            }
        except Exception as exc:  # noqa: BLE001 - surface DB errors to caller
            raise ConnectorError(f"PostgreSQL query failed: {exc}") from exc
        finally:
            if conn is not None:
                await conn.close()
