"""
Integration tests for Alembic database migrations.

This module tests migration functionality to ensure:
1. Migrations can upgrade and downgrade successfully (bidirectional)
2. Schema matches data-model.md specifications (all 7 tables, columns, indexes, constraints)
3. Migrations are idempotent (can run upgrade multiple times)
4. Rollback preserves data integrity

Test Requirements (T029E):
- Test alembic upgrade/downgrade functionality (both directions work correctly)
- Verify schema matches data-model.md specifications (all 7 tables, columns, indexes, constraints)
- Test that migrations are idempotent (can run upgrade multiple times)
- Test rollback preserves data integrity

Test Coverage:
- 12 comprehensive migration integration tests
- Upgrade/downgrade cycle validation
- Schema structure verification (tables, columns, indexes, constraints)
- Idempotency testing
- Data integrity during rollback
- Foreign key constraint validation
- Index existence verification

Test Isolation:
- Tests use TEST_DATABASE_URL with dedicated test schema
- Each test creates/drops all tables for isolation
- No interference with production database

Running Tests:
- Requires PostgreSQL database (migrations are PostgreSQL-specific)
- Set TEST_DATABASE_URL environment variable:
  export TEST_DATABASE_URL="postgresql://user:pass@host:port/db"
- Run tests:
  pytest tests/integration/test_migrations.py -v
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text, MetaData, Table
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncConnection
from sqlalchemy.pool import NullPool

# Add src directory to Python path for imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir / "src"))

from src.lib.database import Base
from src.models.user import User
from src.models.quiz_response import QuizResponse
from src.models.meal_plan import MealPlan
from src.models.payment_transaction import PaymentTransaction
from src.models.manual_resolution import ManualResolution
from src.models.magic_link import MagicLinkToken
from src.models.email_blacklist import EmailBlacklist


# ============================================================================
# Helper Functions for URL Conversion
# ============================================================================


def convert_url_for_asyncpg(db_url: str) -> str:
    """
    Convert PostgreSQL database URL to asyncpg-compatible format.

    Asyncpg doesn't support all PostgreSQL URL parameters. This function:
    1. Converts postgresql:// to postgresql+asyncpg://
    2. Replaces sslmode=require with ssl=require
    3. Removes unsupported query parameters (channel_binding, etc.)

    Args:
        db_url: Original PostgreSQL database URL

    Returns:
        asyncpg-compatible database URL
    """
    # Convert to asyncpg driver
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not db_url.startswith("postgresql+asyncpg://"):
        db_url = f"postgresql+asyncpg://{db_url}"

    # Split URL at '?' to separate base URL and query parameters
    if '?' in db_url:
        base_url, query_string = db_url.split('?', 1)
        query_params = parse_qs(query_string)

        # Keep only supported asyncpg parameters
        asyncpg_params = {}

        # Convert sslmode to ssl
        if 'sslmode' in query_params:
            ssl_value = query_params['sslmode'][0]
            if ssl_value == 'require':
                asyncpg_params['ssl'] = 'require'
        elif 'ssl' in query_params:
            asyncpg_params['ssl'] = query_params['ssl'][0]

        # Rebuild URL with cleaned parameters
        if asyncpg_params:
            new_query = '&'.join(f"{k}={v}" for k, v in asyncpg_params.items())
            return f"{base_url}?{new_query}"
        else:
            return base_url
    else:
        return db_url


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    """
    Create Alembic configuration for migration testing.

    Returns:
        Alembic Config object pointing to backend/alembic.ini
    """
    alembic_ini_path = backend_dir / "alembic.ini"
    config = Config(str(alembic_ini_path))

    # Override database URL with test database URL
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if test_db_url:
        # Convert to asyncpg-compatible format
        test_db_url = convert_url_for_asyncpg(test_db_url)
        config.set_main_option("sqlalchemy.url", test_db_url)

    return config


@pytest_asyncio.fixture(scope="function")
async def migration_engine() -> AsyncEngine:
    """
    Create dedicated test database engine for migration testing.

    Uses NullPool to avoid connection pooling issues during migration testing.
    Each test gets a fresh engine with clean schema.
    """
    test_db_url = os.getenv("TEST_DATABASE_URL")

    if not test_db_url:
        pytest.skip("TEST_DATABASE_URL not set - PostgreSQL required for migration tests")

    # Convert to asyncpg-compatible format
    test_db_url = convert_url_for_asyncpg(test_db_url)

    engine = create_async_engine(
        test_db_url,
        poolclass=NullPool,
        echo=False,
    )

    yield engine

    # Cleanup: drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def clean_migration_db(migration_engine: AsyncEngine):
    """
    Ensure database is clean before migration test.

    Drops all existing tables to provide clean slate for migration testing.
    """
    async with migration_engine.begin() as conn:
        # Drop all tables if they exist
        await conn.run_sync(Base.metadata.drop_all)

    yield

    # Cleanup after test
    async with migration_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ============================================================================
# Helper Functions
# ============================================================================


async def get_table_names(connection: AsyncConnection) -> List[str]:
    """
    Get list of all table names in the database.

    Args:
        connection: SQLAlchemy async connection

    Returns:
        List of table names
    """
    def _get_tables(sync_conn):
        inspector = inspect(sync_conn)
        return inspector.get_table_names()

    return await connection.run_sync(_get_tables)


async def get_table_columns(connection: AsyncConnection, table_name: str) -> List[Dict[str, Any]]:
    """
    Get column information for a specific table.

    Args:
        connection: SQLAlchemy async connection
        table_name: Name of the table

    Returns:
        List of column dictionaries with name, type, nullable info
    """
    def _get_columns(sync_conn):
        inspector = inspect(sync_conn)
        return inspector.get_columns(table_name)

    return await connection.run_sync(_get_columns)


async def get_table_indexes(connection: AsyncConnection, table_name: str) -> List[Dict[str, Any]]:
    """
    Get index information for a specific table.

    Args:
        connection: SQLAlchemy async connection
        table_name: Name of the table

    Returns:
        List of index dictionaries
    """
    def _get_indexes(sync_conn):
        inspector = inspect(sync_conn)
        return inspector.get_indexes(table_name)

    return await connection.run_sync(_get_indexes)


async def get_foreign_keys(connection: AsyncConnection, table_name: str) -> List[Dict[str, Any]]:
    """
    Get foreign key constraints for a specific table.

    Args:
        connection: SQLAlchemy async connection
        table_name: Name of the table

    Returns:
        List of foreign key constraint dictionaries
    """
    def _get_fks(sync_conn):
        inspector = inspect(sync_conn)
        return inspector.get_foreign_keys(table_name)

    return await connection.run_sync(_get_fks)


async def get_unique_constraints(connection: AsyncConnection, table_name: str) -> List[Dict[str, Any]]:
    """
    Get unique constraints for a specific table.

    Args:
        connection: SQLAlchemy async connection
        table_name: Name of the table

    Returns:
        List of unique constraint dictionaries
    """
    def _get_uniques(sync_conn):
        inspector = inspect(sync_conn)
        return inspector.get_unique_constraints(table_name)

    return await connection.run_sync(_get_uniques)


def run_alembic_upgrade(alembic_config: Config, revision: str = "head"):
    """
    Run alembic upgrade to specified revision.

    Args:
        alembic_config: Alembic configuration
        revision: Target revision (default: "head")
    """
    command.upgrade(alembic_config, revision)


def run_alembic_downgrade(alembic_config: Config, revision: str = "base"):
    """
    Run alembic downgrade to specified revision.

    Args:
        alembic_config: Alembic configuration
        revision: Target revision (default: "base")
    """
    command.downgrade(alembic_config, revision)


# ============================================================================
# Migration Upgrade/Downgrade Tests
# ============================================================================


@pytest.mark.asyncio
async def test_migration_upgrade_creates_all_tables(
    alembic_config: Config,
    migration_engine: AsyncEngine,
    clean_migration_db
):
    """Test that running upgrade creates all 7 required tables."""
    # Run upgrade
    run_alembic_upgrade(alembic_config, "head")

    # Verify all tables exist
    async with migration_engine.connect() as conn:
        tables = await get_table_names(conn)

    expected_tables = {
        "users",
        "quiz_responses",
        "meal_plans",
        "payment_transactions",
        "manual_resolution",
        "magic_link_tokens",
        "email_blacklist",
    }

    assert expected_tables.issubset(set(tables)), f"Missing tables: {expected_tables - set(tables)}"


@pytest.mark.asyncio
async def test_migration_downgrade_removes_all_tables(
    alembic_config: Config,
    migration_engine: AsyncEngine,
    clean_migration_db
):
    """Test that running downgrade removes all tables."""
    # Run upgrade first
    run_alembic_upgrade(alembic_config, "head")

    # Verify tables exist
    async with migration_engine.connect() as conn:
        tables_before = await get_table_names(conn)
    assert len(tables_before) > 0

    # Run downgrade
    run_alembic_downgrade(alembic_config, "base")

    # Verify tables are removed
    async with migration_engine.connect() as conn:
        tables_after = await get_table_names(conn)

    app_tables = [t for t in tables_after if t not in ("alembic_version",)]
    assert len(app_tables) == 0, f"Tables still exist after downgrade: {app_tables}"


@pytest.mark.asyncio
async def test_migration_upgrade_downgrade_cycle(
    alembic_config: Config,
    migration_engine: AsyncEngine,
    clean_migration_db
):
    """Test that upgrade -> downgrade -> upgrade cycle works correctly."""
    # First upgrade
    run_alembic_upgrade(alembic_config, "head")
    async with migration_engine.connect() as conn:
        tables_after_upgrade1 = await get_table_names(conn)
    assert len(tables_after_upgrade1) > 0

    # Downgrade
    run_alembic_downgrade(alembic_config, "base")
    async with migration_engine.connect() as conn:
        tables_after_downgrade = await get_table_names(conn)
    app_tables = [t for t in tables_after_downgrade if t not in ("alembic_version",)]
    assert len(app_tables) == 0

    # Second upgrade
    run_alembic_upgrade(alembic_config, "head")
    async with migration_engine.connect() as conn:
        tables_after_upgrade2 = await get_table_names(conn)

    # Verify same tables created both times
    assert set(tables_after_upgrade1) == set(tables_after_upgrade2)


# ============================================================================
# Schema Verification Tests
# ============================================================================


@pytest.mark.asyncio
async def test_users_table_schema(
    alembic_config: Config,
    migration_engine: AsyncEngine,
    clean_migration_db
):
    """Test that users table has correct columns, indexes, and constraints."""
    run_alembic_upgrade(alembic_config, "head")

    async with migration_engine.connect() as conn:
        # Check columns
        columns = await get_table_columns(conn, "users")
        column_names = {col["name"] for col in columns}

        expected_columns = {
            "id", "email", "normalized_email", "password_hash",
            "created_at", "updated_at"
        }
        assert expected_columns == column_names

        # Check indexes
        indexes = await get_table_indexes(conn, "users")
        index_names = {idx["name"] for idx in indexes}

        # Should have indexes on email and normalized_email
        assert "idx_user_email" in index_names
        assert "idx_user_normalized_email" in index_names or "ix_users_normalized_email" in index_names

        # Check unique constraints
        uniques = await get_unique_constraints(conn, "users")
        unique_columns = []
        for unique in uniques:
            unique_columns.extend(unique.get("column_names", []))

        # Email should be unique
        assert "email" in unique_columns


@pytest.mark.asyncio
async def test_quiz_responses_table_schema(
    alembic_config: Config,
    migration_engine: AsyncEngine,
    clean_migration_db
):
    """Test that quiz_responses table has correct columns, indexes, and foreign keys."""
    run_alembic_upgrade(alembic_config, "head")

    async with migration_engine.connect() as conn:
        # Check columns
        columns = await get_table_columns(conn, "quiz_responses")
        column_names = {col["name"] for col in columns}

        expected_columns = {
            "id", "user_id", "email", "normalized_email", "quiz_data",
            "calorie_target", "created_at", "payment_id", "pdf_delivered_at"
        }
        assert expected_columns == column_names

        # Check JSONB column type
        quiz_data_col = next(col for col in columns if col["name"] == "quiz_data")
        assert "JSONB" in str(quiz_data_col["type"]).upper()

        # Check foreign keys
        fks = await get_foreign_keys(conn, "quiz_responses")
        assert len(fks) > 0
        fk_columns = [fk["constrained_columns"][0] for fk in fks]
        assert "user_id" in fk_columns

        # Check indexes
        indexes = await get_table_indexes(conn, "quiz_responses")
        index_names = {idx["name"] for idx in indexes}
        assert "idx_quiz_normalized_email" in index_names
        assert "idx_quiz_created_at" in index_names
        assert "idx_quiz_pdf_delivered_at" in index_names


@pytest.mark.asyncio
async def test_meal_plans_table_schema(
    alembic_config: Config,
    migration_engine: AsyncEngine,
    clean_migration_db
):
    """Test that meal_plans table has correct columns, indexes, and constraints."""
    run_alembic_upgrade(alembic_config, "head")

    async with migration_engine.connect() as conn:
        # Check columns
        columns = await get_table_columns(conn, "meal_plans")
        column_names = {col["name"] for col in columns}

        expected_columns = {
            "id", "payment_id", "email", "normalized_email", "pdf_blob_path",
            "calorie_target", "preferences_summary", "ai_model", "status",
            "refund_count", "created_at", "email_sent_at"
        }
        assert expected_columns == column_names

        # Check JSONB column type
        prefs_col = next(col for col in columns if col["name"] == "preferences_summary")
        assert "JSONB" in str(prefs_col["type"]).upper()

        # Check unique constraints
        uniques = await get_unique_constraints(conn, "meal_plans")
        unique_columns = []
        for unique in uniques:
            unique_columns.extend(unique.get("column_names", []))

        # payment_id should be unique
        assert "payment_id" in unique_columns

        # Check indexes
        indexes = await get_table_indexes(conn, "meal_plans")
        index_names = {idx["name"] for idx in indexes}
        assert "idx_mealplan_payment_id" in index_names
        assert "idx_mealplan_normalized_email" in index_names
        assert "idx_mealplan_created_at" in index_names


@pytest.mark.asyncio
async def test_payment_transactions_table_schema(
    alembic_config: Config,
    migration_engine: AsyncEngine,
    clean_migration_db
):
    """Test that payment_transactions table has correct columns and foreign keys."""
    run_alembic_upgrade(alembic_config, "head")

    async with migration_engine.connect() as conn:
        # Check columns
        columns = await get_table_columns(conn, "payment_transactions")
        column_names = {col["name"] for col in columns}

        expected_columns = {
            "id", "payment_id", "meal_plan_id", "amount", "currency",
            "payment_method", "payment_status", "paddle_created_at",
            "webhook_received_at", "customer_email", "normalized_email",
            "created_at", "updated_at"
        }
        assert expected_columns == column_names

        # Check foreign keys
        fks = await get_foreign_keys(conn, "payment_transactions")
        assert len(fks) > 0
        fk_columns = [fk["constrained_columns"][0] for fk in fks]
        assert "meal_plan_id" in fk_columns

        # Check unique constraints
        uniques = await get_unique_constraints(conn, "payment_transactions")
        unique_columns = []
        for unique in uniques:
            unique_columns.extend(unique.get("column_names", []))

        # payment_id should be unique
        assert "payment_id" in unique_columns


@pytest.mark.asyncio
async def test_manual_resolution_table_schema(
    alembic_config: Config,
    migration_engine: AsyncEngine,
    clean_migration_db
):
    """Test that manual_resolution table has correct columns and indexes."""
    run_alembic_upgrade(alembic_config, "head")

    async with migration_engine.connect() as conn:
        # Check columns
        columns = await get_table_columns(conn, "manual_resolution")
        column_names = {col["name"] for col in columns}

        expected_columns = {
            "id", "payment_id", "user_email", "normalized_email",
            "issue_type", "status", "sla_deadline", "created_at",
            "resolved_at", "assigned_to", "resolution_notes"
        }
        assert expected_columns == column_names

        # Check indexes
        indexes = await get_table_indexes(conn, "manual_resolution")
        index_names = {idx["name"] for idx in indexes}
        assert "idx_manual_sla_deadline" in index_names or "ix_manual_resolution_sla_deadline" in index_names
        assert "idx_manual_status" in index_names
        assert "idx_manual_created_at" in index_names or "ix_manual_resolution_created_at" in index_names


@pytest.mark.asyncio
async def test_magic_link_tokens_table_schema(
    alembic_config: Config,
    migration_engine: AsyncEngine,
    clean_migration_db
):
    """Test that magic_link_tokens table has correct columns and constraints."""
    run_alembic_upgrade(alembic_config, "head")

    async with migration_engine.connect() as conn:
        # Check columns
        columns = await get_table_columns(conn, "magic_link_tokens")
        column_names = {col["name"] for col in columns}

        expected_columns = {
            "id", "token_hash", "email", "normalized_email",
            "created_at", "expires_at", "used_at", "generation_ip", "usage_ip"
        }
        assert expected_columns == column_names

        # Check unique constraints
        uniques = await get_unique_constraints(conn, "magic_link_tokens")
        unique_columns = []
        for unique in uniques:
            unique_columns.extend(unique.get("column_names", []))

        # token_hash should be unique
        assert "token_hash" in unique_columns


@pytest.mark.asyncio
async def test_email_blacklist_table_schema(
    alembic_config: Config,
    migration_engine: AsyncEngine,
    clean_migration_db
):
    """Test that email_blacklist table has correct columns and constraints."""
    run_alembic_upgrade(alembic_config, "head")

    async with migration_engine.connect() as conn:
        # Check columns
        columns = await get_table_columns(conn, "email_blacklist")
        column_names = {col["name"] for col in columns}

        expected_columns = {
            "id", "normalized_email", "reason", "created_at", "expires_at"
        }
        assert expected_columns == column_names

        # Check unique constraints
        uniques = await get_unique_constraints(conn, "email_blacklist")
        unique_columns = []
        for unique in uniques:
            unique_columns.extend(unique.get("column_names", []))

        # normalized_email should be unique
        assert "normalized_email" in unique_columns


# ============================================================================
# Idempotency Tests
# ============================================================================


@pytest.mark.asyncio
async def test_migration_upgrade_is_idempotent(
    alembic_config: Config,
    migration_engine: AsyncEngine,
    clean_migration_db
):
    """Test that running upgrade multiple times doesn't cause errors."""
    # First upgrade
    run_alembic_upgrade(alembic_config, "head")

    async with migration_engine.connect() as conn:
        tables_after_first = await get_table_names(conn)

    # Second upgrade (should be no-op)
    run_alembic_upgrade(alembic_config, "head")

    async with migration_engine.connect() as conn:
        tables_after_second = await get_table_names(conn)

    # Should have same tables
    assert set(tables_after_first) == set(tables_after_second)


@pytest.mark.asyncio
async def test_migration_downgrade_is_idempotent(
    alembic_config: Config,
    migration_engine: AsyncEngine,
    clean_migration_db
):
    """Test that running downgrade multiple times doesn't cause errors."""
    # Upgrade first
    run_alembic_upgrade(alembic_config, "head")

    # First downgrade
    run_alembic_downgrade(alembic_config, "base")

    async with migration_engine.connect() as conn:
        tables_after_first = await get_table_names(conn)
        app_tables_first = [t for t in tables_after_first if t not in ("alembic_version",)]

    # Second downgrade (should be no-op)
    run_alembic_downgrade(alembic_config, "base")

    async with migration_engine.connect() as conn:
        tables_after_second = await get_table_names(conn)
        app_tables_second = [t for t in tables_after_second if t not in ("alembic_version",)]

    # Should have same result (no tables)
    assert app_tables_first == app_tables_second == []


# ============================================================================
# Data Integrity Tests
# ============================================================================


@pytest.mark.asyncio
async def test_rollback_with_data_preserves_integrity(
    alembic_config: Config,
    migration_engine: AsyncEngine,
    clean_migration_db
):
    """Test that downgrade preserves data integrity (no orphaned data)."""
    from datetime import datetime
    from src.lib.email_utils import normalize_email

    # Run upgrade
    run_alembic_upgrade(alembic_config, "head")

    # Insert test data
    async with migration_engine.begin() as conn:
        # Insert user
        await conn.execute(
            text("""
                INSERT INTO users (id, email, normalized_email, password_hash, created_at, updated_at)
                VALUES (:id, :email, :normalized_email, :password_hash, :created_at, :updated_at)
            """),
            {
                "id": "test-user-1",
                "email": "test@example.com",
                "normalized_email": normalize_email("test@example.com"),
                "password_hash": "hashed",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

        # Verify data inserted
        result = await conn.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        assert count == 1

    # Run downgrade - this should clean up all data
    run_alembic_downgrade(alembic_config, "base")

    # Verify tables are gone (so no orphaned data possible)
    async with migration_engine.connect() as conn:
        tables = await get_table_names(conn)
        app_tables = [t for t in tables if t not in ("alembic_version",)]
        assert len(app_tables) == 0

    # Run upgrade again
    run_alembic_upgrade(alembic_config, "head")

    # Verify fresh database (no data from before)
    async with migration_engine.begin() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        assert count == 0, "Database should be clean after upgrade following downgrade"
