"""Alembic migration environment configuration.

Provides offline and online migration entry points. URL resolution prefers
env vars (``DATABASE_URL`` / ``DB_URL``) falling back to alembic.ini.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Interpret the config file for Python logging.
config = context.config
if config.config_file_name is not None:  # pragma: no cover
    fileConfig(config.config_file_name)


def get_url() -> str:
    """Resolve database URL (env overrides config)."""
    return os.getenv(
        "DATABASE_URL",
        os.getenv(
            "DB_URL",
            config.get_main_option(
                "sqlalchemy.url",  # type: ignore[arg-type]
            ),
        ),
    )


# Import models for autogenerate
from db.models import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with an Engine connection."""
    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
        ),  # type: ignore[arg-type]
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=get_url(),
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():  # pragma: no cover
    run_migrations_offline()
else:  # pragma: no cover
    run_migrations_online()
