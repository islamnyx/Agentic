"""Alembic environment configuration (async SQLAlchemy)."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import all models so Alembic can detect them for autogenerate
from gateway.db.session import Base  # noqa: F401
from gateway.models.agent import Agent  # noqa: F401
from gateway.models.agent_token import AgentToken  # noqa: F401
from gateway.models.approval import Approval  # noqa: F401
from gateway.models.audit_entry import AuditEntry  # noqa: F401
from gateway.models.connector_credential import (  # noqa: F401
    ConnectorCredential,
    CredentialLease,
)
from gateway.models.organization import Organization  # noqa: F401
from gateway.models.policy_version import PolicyVersion  # noqa: F401
from gateway.models.user import User  # noqa: F401
from gateway.models.metrics import (  # noqa: F401
    AgentCost,
    DashboardMetric,
    SecurityIncident,
)
from gateway.models.session_context import (  # noqa: F401
    DataLabel,
    SessionAwareRule,
    SessionContext,
    TrustLabel,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations with an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
