"""Connector base classes (Phase 3).

Connectors perform the actual outbound work (HTTP calls, DB queries, email,
browser automation) on behalf of an agent. Every connector receives a
decrypted secret injected by the credential broker -- agents never see it.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any


class ConnectorError(Exception):
    """Raised when a connector cannot complete an operation."""


class ConnectorBase(ABC):
    """Base class for all connectors.

    Subclasses implement :meth:`_run`. ``validate_params`` may be overridden
    to reject unsafe parameters before execution.
    """

    connector_type: str = "base"

    async def execute(
        self, params: dict[str, Any], secret: str | None = None
    ) -> dict[str, Any]:
        """Execute the connector operation with ``params`` and injected ``secret``."""
        self.validate_params(params)
        return await self._run(params, secret)

    def validate_params(self, params: dict[str, Any]) -> None:
        """Validate parameters before execution. Override in subclasses."""
        return None

    @abstractmethod
    async def _run(
        self, params: dict[str, Any], secret: str | None = None
    ) -> dict[str, Any]:
        """Run the connector operation."""

    @staticmethod
    def _dangerous_sql_keywords() -> frozenset[str]:
        return frozenset(
            {
                "insert",
                "update",
                "delete",
                "drop",
                "alter",
                "create",
                "truncate",
                "grant",
                "revoke",
                "attach",
                "detach",
                "copy",
                "vacuum",
                "reindex",
                "cluster",
                "comment",
            }
        )


_DANGEROUS_SQL = re.compile(
    r"\b(" + "|".join(ConnectorBase._dangerous_sql_keywords()) + r")\b",
    re.IGNORECASE,
)


def is_read_only_select(sql: str) -> bool:
    """Return True only if ``sql`` is a single read-only SELECT statement.

    Rejects any statement containing DDL/DML keywords or multiple statements.
    """
    stripped = sql.strip().rstrip(";")
    if not stripped.lower().startswith("select"):
        return False
    if ";" in stripped:
        return False
    if _DANGEROUS_SQL.search(stripped):
        return False
    return True


def has_parameter_placeholders(sql: str) -> bool:
    """Return True if ``sql`` uses parameter placeholders ($1, $2, :name, ?)."""
    return bool(
        re.search(r"\$[0-9]+", sql)
        or re.search(r":\w+", sql)
        or "?" in sql
    )


# Connector registry: connector_type -> connector class
_CONNECTOR_CLASSES: dict[str, type[ConnectorBase]] = {}


def register_connector(connector_type: str, cls: type[ConnectorBase]) -> None:
    """Register a connector implementation for ``connector_type``."""
    _CONNECTOR_CLASSES[connector_type] = cls


def build_connector(connector_type: str, config: dict[str, Any] | None = None) -> ConnectorBase:
    """Build a connector instance for ``connector_type`` with ``config``."""
    cls = _CONNECTOR_CLASSES.get(connector_type)
    if cls is None:
        raise ConnectorError(f"No connector registered for type {connector_type!r}")
    return cls(config or {})


# Register built-in connectors
from gateway.connectors.http import HttpConnector  # noqa: E402
from gateway.connectors.playwright import PlaywrightConnector  # noqa: E402
from gateway.connectors.postgres import PostgresConnector  # noqa: E402
from gateway.connectors.smtp import SmtpConnector  # noqa: E402

register_connector("http", HttpConnector)
register_connector("postgres", PostgresConnector)
register_connector("smtp", SmtpConnector)
register_connector("playwright", PlaywrightConnector)
