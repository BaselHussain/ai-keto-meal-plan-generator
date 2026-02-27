"""
Database Connection Utility for Neon DB (Serverless PostgreSQL)

This module provides async SQLAlchemy session management with connection pooling
optimized for Neon's serverless PostgreSQL architecture.

Key Features:
- AsyncEngine with asyncpg driver for non-blocking I/O
- Connection pooling with serverless-friendly settings
- Dependency injection pattern for FastAPI endpoints
- Proper session lifecycle management (commit/rollback)
- Error handling and logging integration

Usage:
    from src.lib.database import get_db
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession

    @app.get("/users")
    async def get_users(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(User))
        users = result.scalars().all()
        return users
"""

import os
import ssl
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy.orm import declarative_base

# Configure logging
logger = logging.getLogger(__name__)

# SQLAlchemy declarative base for ORM models
Base = declarative_base()

# Global engine instance (initialized at startup)
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_database_url() -> str:
    """
    Get database URL from environment variables.

    Returns:
        str: PostgreSQL connection string for asyncpg driver

    Raises:
        ValueError: If NEON_DATABASE_URL is not set
    """
    database_url = os.getenv("NEON_DATABASE_URL")

    if not database_url:
        raise ValueError(
            "NEON_DATABASE_URL environment variable is not set. "
            "Please configure your Neon DB connection string in .env file."
        )

    # Convert postgresql:// to postgresql+asyncpg:// for async driver
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not database_url.startswith("postgresql+asyncpg://"):
        database_url = f"postgresql+asyncpg://{database_url}"

    # Strip query params that asyncpg doesn't understand (sslmode, channel_binding)
    # SSL is handled via connect_args in create_engine instead
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    parsed = urlparse(database_url)
    params = parse_qs(parsed.query)
    # Remove psycopg2-specific params that asyncpg doesn't support
    for key in ["sslmode", "channel_binding"]:
        params.pop(key, None)
    clean_query = urlencode(params, doseq=True)
    database_url = urlunparse(parsed._replace(query=clean_query))

    return database_url


def create_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy engine with Neon DB connection pooling.

    Connection Pool Settings (optimized for serverless Neon):
    - pool_size: 5 - Maximum number of persistent connections
    - max_overflow: 10 - Additional connections beyond pool_size
    - pool_timeout: 30s - Maximum time to wait for connection from pool
    - pool_recycle: 3600s (1 hour) - Recycle connections to prevent stale connections
    - pool_pre_ping: True - Verify connections before using (detect disconnects)

    For serverless environments (Vercel, AWS Lambda):
    - Use NullPool to disable connection pooling (creates new connection per request)
    - Prevents connection exhaustion in ephemeral compute environments

    Returns:
        AsyncEngine: Configured async database engine
    """
    database_url = get_database_url()
    env = os.getenv("ENV", "development")

    # Determine pooling strategy based on environment
    # Serverless/production: Use NullPool (no persistent connections)
    # Development: Use AsyncAdaptedQueuePool (connection pooling)
    if env == "production" or os.getenv("SERVERLESS", "false").lower() == "true":
        # NullPool for serverless environments (Vercel, Lambda)
        # Each request creates a new connection, closed after response
        poolclass = NullPool
        logger.info("Using NullPool (serverless mode) for database connections")

        # Create SSL context for Neon DB (asyncpg needs explicit SSL)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        engine = create_async_engine(
            database_url,
            poolclass=poolclass,
            echo=False,  # Disable SQL query logging in production
            future=True,  # Use SQLAlchemy 2.0 style
            connect_args={"ssl": ssl_context},
        )
    else:
        # AsyncAdaptedQueuePool for development (connection pooling)
        logger.info("Using AsyncAdaptedQueuePool (connection pooling) for database connections")

        # Create SSL context for Neon DB (asyncpg needs explicit SSL)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        engine = create_async_engine(
            database_url,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=5,  # Number of persistent connections
            max_overflow=10,  # Additional connections beyond pool_size
            pool_timeout=30,  # Seconds to wait for connection
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Verify connection health before use
            echo=env == "development",  # Log SQL queries in development
            future=True,  # Use SQLAlchemy 2.0 style
            connect_args={"ssl": ssl_context},
        )

    logger.info(f"Database engine created successfully (environment: {env})")
    return engine


def init_db() -> None:
    """
    Initialize database connection (called at application startup).

    This should be called once during FastAPI application startup:
        @app.on_event("startup")
        async def startup():
            init_db()
    """
    global _engine, _async_session_factory

    if _engine is not None:
        logger.warning("Database engine already initialized")
        return

    _engine = create_engine()
    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Prevent lazy-loading errors after commit
        autocommit=False,  # Explicit transaction control
        autoflush=False,  # Manual flush control for better performance
    )

    logger.info("Database session factory initialized")


async def close_db() -> None:
    """
    Close database connections (called at application shutdown).

    This should be called during FastAPI application shutdown:
        @app.on_event("shutdown")
        async def shutdown():
            await close_db()
    """
    global _engine, _async_session_factory

    if _engine is None:
        logger.warning("Database engine not initialized")
        return

    await _engine.dispose()
    _engine = None
    _async_session_factory = None

    logger.info("Database connections closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session management.

    Provides async database session with automatic:
    - Transaction management (commit on success, rollback on error)
    - Session cleanup (close after request)
    - Error handling and logging

    Usage:
        @app.post("/users")
        async def create_user(
            user_data: UserCreate,
            db: AsyncSession = Depends(get_db)
        ):
            user = User(**user_data.dict())
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user

    Yields:
        AsyncSession: Database session for request

    Raises:
        RuntimeError: If database not initialized (call init_db() first)
    """
    if _async_session_factory is None:
        raise RuntimeError(
            "Database not initialized. Call init_db() during application startup."
        )

    # Create new session for this request
    async with _async_session_factory() as session:
        try:
            yield session
            # Commit transaction if no exceptions occurred
            await session.commit()
        except Exception as e:
            # Rollback transaction on any error
            await session.rollback()
            logger.error(f"Database transaction error: {str(e)}", exc_info=True)
            raise
        finally:
            # Ensure session is closed
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database session management in non-FastAPI contexts.

    Use this when you need a database session outside of a FastAPI dependency
    injection context (e.g., background tasks, scheduled jobs, service functions
    called directly from other services).

    Unlike ``get_db`` (which is an async generator for FastAPI's Depends),
    this function is a proper async context manager and supports the
    ``async with`` statement.

    Usage::

        async with get_db_context() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()

    Yields:
        AsyncSession: Database session

    Raises:
        RuntimeError: If database not initialized (call init_db() first)
    """
    if _async_session_factory is None:
        raise RuntimeError(
            "Database not initialized. Call init_db() during application startup."
        )

    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database transaction error: {str(e)}", exc_info=True)
            raise
        finally:
            await session.close()


def get_engine() -> AsyncEngine:
    """
    Get the global database engine instance.

    Useful for direct engine access (e.g., for Alembic migrations).

    Returns:
        AsyncEngine: Global database engine

    Raises:
        RuntimeError: If database not initialized
    """
    if _engine is None:
        raise RuntimeError(
            "Database engine not initialized. Call init_db() during application startup."
        )
    return _engine


async def health_check() -> dict:
    """
    Check database connection health.

    Executes a simple query to verify database connectivity.
    Useful for health check endpoints and monitoring.

    Returns:
        dict: Health status with connection details

    Example:
        {
            "status": "healthy",
            "database": "connected",
            "pool_size": 5,
            "pool_overflow": 10
        }
    """
    if _engine is None:
        return {
            "status": "unhealthy",
            "database": "not_initialized",
            "error": "Database engine not initialized"
        }

    try:
        async with _async_session_factory() as session:
            # Execute simple query to verify connection
            result = await session.execute(text("SELECT 1"))
            result.scalar()

            # Get pool statistics (if using connection pool)
            pool_stats = {}
            if hasattr(_engine.pool, 'size'):
                pool_stats = {
                    "pool_size": _engine.pool.size(),
                    "pool_overflow": _engine.pool.overflow(),
                    "pool_checked_out": _engine.pool.checkedout(),
                }

            return {
                "status": "healthy",
                "database": "connected",
                **pool_stats
            }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e)
        }
