"""
Pytest configuration and fixtures.

This file sets up the Python path to allow imports from src/ directory
and provides database fixtures for integration testing.
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

# Add src directory to Python path for imports
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

# Import Base after path is set
from src.lib.database import Base


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test database URL fixture
@pytest.fixture(scope="session")
def test_database_url() -> str:
    """
    Get test database URL from environment or create in-memory SQLite database.

    For integration tests, use a separate test database to avoid polluting production data.
    Options:
    1. Set TEST_DATABASE_URL environment variable
    2. Fallback to SQLite in-memory database (for unit tests)
    """
    test_db_url = os.getenv("TEST_DATABASE_URL")

    if test_db_url:
        # Use PostgreSQL test database if provided
        if test_db_url.startswith("postgresql://"):
            test_db_url = test_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not test_db_url.startswith("postgresql+asyncpg://"):
            test_db_url = f"postgresql+asyncpg://{test_db_url}"
        return test_db_url
    else:
        # Fallback to SQLite in-memory database for local testing
        # Note: SQLite has limitations (no JSONB support), so PostgreSQL is recommended
        return "sqlite+aiosqlite:///:memory:"


# Test database engine fixture
@pytest_asyncio.fixture(scope="session")
async def test_engine(test_database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """
    Create test database engine with NullPool (no connection pooling).

    Uses NullPool to create fresh connections for each test, preventing
    connection state leakage between tests.
    """
    engine = create_async_engine(
        test_database_url,
        poolclass=NullPool,
        echo=False,  # Set to True for SQL query debugging
        future=True,
    )

    # Create all tables in test database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables and dispose engine after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# Test database session fixture
@pytest_asyncio.fixture
async def test_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create test database session with automatic rollback after each test.

    Each test gets a fresh session that is rolled back after the test completes,
    ensuring test isolation and preventing data leakage between tests.
    """
    # Create session factory
    async_session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Create session and begin transaction
    async with async_session_factory() as session:
        async with session.begin():
            yield session
            # Rollback transaction after test (automatic cleanup)
            await session.rollback()
