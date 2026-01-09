import asyncio
import os
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load database URL from environment variable and convert for asyncpg
DATABASE_URL = os.getenv("NEON_DATABASE_URL")
if DATABASE_URL:
    # Parse the URL
    parsed = urlparse(DATABASE_URL)

    # Replace postgresql:// with postgresql+asyncpg:// for async support
    scheme = parsed.scheme.replace("postgresql", "postgresql+asyncpg")

    # Parse query parameters
    query_params = parse_qs(parsed.query)

    # Convert sslmode to ssl for asyncpg compatibility
    # asyncpg expects ssl='require' or other valid SSL modes
    if "sslmode" in query_params:
        ssl_mode = query_params["sslmode"][0]
        # asyncpg accepts: disable, allow, prefer, require, verify-ca, verify-full
        query_params["ssl"] = [ssl_mode]
        del query_params["sslmode"]

    # Remove channel_binding as asyncpg doesn't support it in connection URL
    if "channel_binding" in query_params:
        del query_params["channel_binding"]

    # Reconstruct query string (flatten lists to single values)
    new_query = urlencode({k: v[0] for k, v in query_params.items()})

    # Reconstruct the URL
    DATABASE_URL = urlunparse((scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    config.set_main_option("sqlalchemy.url", DATABASE_URL)

# add your model's MetaData object here
# for 'autogenerate' support
# When models are created in Phase 2, import them here:
# from database.models import Base
# target_metadata = Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using async engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
