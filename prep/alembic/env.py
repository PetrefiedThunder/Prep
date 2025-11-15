"""Alembic environment configuration."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add project root to Python path to allow imports
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from prep.models.db import get_db_url  # noqa: E402
from prep.models.orm import Base  # noqa: E402


def _configure_sqlalchemy_url(cfg) -> None:
    url = cfg.get_main_option("sqlalchemy.url")
    if not url:
        cfg.set_main_option("sqlalchemy.url", get_db_url())


def _import_model_modules() -> None:
    """Import model packages so their tables register on the metadata."""

    import prep.regulatory.models  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_configure_sqlalchemy_url(config)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    _import_model_modules()

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    _import_model_modules()

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
