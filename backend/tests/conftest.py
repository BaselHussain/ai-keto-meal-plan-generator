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
from sqlalchemy import text, JSON
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool, StaticPool
from httpx import AsyncClient, ASGITransport

# Add src directory to Python path for imports
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

# Load .env so TEST_DATABASE_URL / NEON_DATABASE_URL are available to migration tests
try:
    from dotenv import load_dotenv
    load_dotenv(backend_dir / ".env")
except ImportError:
    pass

# ---------------------------------------------------------------------------
# SQLite / JSONB compatibility shim
# ---------------------------------------------------------------------------
# PostgreSQL's JSONB type is not supported by SQLite.  When no
# TEST_DATABASE_URL is set we fall back to an in-memory SQLite DB, so we
# patch the SQLite type compiler to render JSONB columns as plain JSON.
# This must happen before any SQLAlchemy models are imported.
if not os.getenv("TEST_DATABASE_URL"):
    try:
        from sqlalchemy.dialects.postgresql import JSONB
        from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

        if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):
            def _visit_JSONB(self, type_, **kw):  # type: ignore[override]
                return self.visit_JSON(JSON(), **kw)

            SQLiteTypeCompiler.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]
    except Exception:
        pass

# Import Base after the compatibility shim is in place
from src.lib.database import Base


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the whole test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def test_database_url() -> str:
    """
    Return the database URL for the test session.

    Priority:
    1. TEST_DATABASE_URL env var  →  async PostgreSQL URL
    2. Fallback                   →  shared in-memory SQLite URL

    Note: The SQLite fallback uses a named in-memory file so that all
    aiosqlite connections within the same process share the same database
    (``mode=memory&cache=shared`` + ``StaticPool``).  Plain
    ``sqlite+aiosqlite:///:memory:`` would give each connection a separate
    empty database, causing "no such table" errors.
    """
    test_db_url = os.getenv("TEST_DATABASE_URL")

    if test_db_url:
        if test_db_url.startswith("postgresql://"):
            test_db_url = test_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not test_db_url.startswith("postgresql+asyncpg://"):
            test_db_url = f"postgresql+asyncpg://{test_db_url}"
        return test_db_url

    # Shared in-memory SQLite – all connections see the same database.
    return "sqlite+aiosqlite:///file:test_keto?mode=memory&cache=shared&uri=true"


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session")
async def test_engine(test_database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """
    Create the SQLAlchemy async engine for the test session.

    For SQLite we use StaticPool so that every connection (including those
    created by aiosqlite internally) reuses the same in-memory database that
    was populated by ``Base.metadata.create_all``.

    For PostgreSQL we use NullPool so that there are no persistent connections
    between tests.
    """
    is_sqlite = test_database_url.startswith("sqlite")

    if is_sqlite:
        engine = create_async_engine(
            test_database_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            echo=False,
            future=True,
        )
    else:
        engine = create_async_engine(
            test_database_url,
            poolclass=NullPool,
            echo=False,
            future=True,
        )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Tear down
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

    # Create session without explicit transaction block
    # This allows endpoints to manage their own transactions (commit/rollback)
    async with async_session_factory() as session:
        yield session
        # Rollback any uncommitted changes after test (automatic cleanup)
        await session.rollback()


# Alias for test_session (for backward compatibility)
@pytest_asyncio.fixture
async def async_db(test_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """
    Alias for test_session fixture (for backward compatibility).

    Provides async database session for integration tests.
    """
    yield test_session


# Test client fixture
@pytest_asyncio.fixture
async def async_client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create test HTTP client with FastAPI app.

    Provides AsyncClient for making HTTP requests to FastAPI endpoints
    during integration tests. Database session is overridden to use
    test database.
    """
    # Import app here to avoid circular imports
    from src.main import app
    from src.lib.database import get_db

    # Override get_db dependency to use test session
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    # Create async client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clear dependency overrides after test
    app.dependency_overrides.clear()


# Alias for async_client (for backward compatibility)
@pytest_asyncio.fixture
async def client(async_client: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    """
    Alias for async_client fixture (for backward compatibility).

    Provides HTTP client for integration tests.
    """
    yield async_client


# Alias for test_session (db_session)
@pytest_asyncio.fixture
async def db_session(test_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """
    Alias for test_session fixture (for backward compatibility).

    Provides database session for integration tests.
    """
    yield test_session


# Sample meal plan fixture
@pytest_asyncio.fixture
async def sample_meal_plan(db_session: AsyncSession):
    """
    Create a sample meal plan for testing.

    Returns a completed meal plan with PDF available.
    Uses a unique payment_id per test invocation to avoid UNIQUE constraint
    violations when the shared in-memory SQLite database is used.
    """
    import uuid
    from datetime import datetime, timedelta
    from src.models.meal_plan import MealPlan
    from src.lib.email_utils import normalize_email

    meal_plan = MealPlan(
        payment_id=f"pay_test_{uuid.uuid4().hex[:12]}",
        email="test@example.com",
        normalized_email=normalize_email("test@example.com"),
        pdf_blob_path="https://blob.vercel-storage.com/test-meal-plan.pdf",
        calorie_target=1650,
        preferences_summary={
            "excluded_foods": ["beef", "pork"],
            "preferred_proteins": ["chicken", "fish"],
            "dietary_restrictions": "No dairy"
        },
        ai_model="gpt-4o",
        status="completed",
        email_sent_at=datetime.utcnow() - timedelta(hours=1),  # Sent 1 hour ago (outside grace period)
        created_at=datetime.utcnow() - timedelta(hours=2),
    )

    db_session.add(meal_plan)
    await db_session.commit()
    await db_session.refresh(meal_plan)

    return meal_plan


# Redis client fixture
@pytest_asyncio.fixture
async def redis_client():
    """
    Provide Redis client for integration tests.

    Uses test Redis instance to avoid polluting production data.
    """
    from src.lib.redis_client import get_redis

    redis = await get_redis()
    yield redis

    # Clean up test keys after test
    # Note: In production tests, you might want to use a separate Redis DB
    # or flush specific test keys only
    # await redis.flushdb()  # Use with caution - only in isolated test environment
