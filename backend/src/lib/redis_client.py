"""
Redis connection utility with connection pooling and async support.

This module provides a centralized Redis client for distributed locks,
rate limiting, and caching operations. Supports both standard Redis
and Upstash Redis REST API.

Usage:
    from src.lib.redis_client import get_redis, redis_health_check

    redis = await get_redis()
    await redis.set("key", "value", ex=60)

    # Health check
    is_healthy = await redis_health_check()
"""

import os
import logging
from typing import Optional, Any
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import (
    RedisError,
    ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError,
)

# Configure logging
logger = logging.getLogger(__name__)

# Global connection pool (singleton pattern)
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


def _get_redis_url() -> str:
    """
    Get Redis connection URL from environment variables.

    Supports two modes:
    1. Standard Redis: REDIS_URL (e.g., redis://localhost:6379/0)
    2. Upstash REST API: UPSTASH_REDIS_REST_URL (for serverless)

    Returns:
        str: Redis connection URL

    Raises:
        ValueError: If no Redis URL is configured
    """
    # Standard Redis URL
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis_url

    # Upstash REST API (alternative for serverless)
    upstash_url = os.getenv("UPSTASH_REDIS_REST_URL")
    if upstash_url:
        # For Upstash, we'll use the HTTP interface
        # This is a placeholder - actual Upstash integration may differ
        logger.warning(
            "UPSTASH_REDIS_REST_URL detected. Using standard Redis client. "
            "Consider using upstash-redis package for optimal Upstash support."
        )
        return upstash_url

    raise ValueError(
        "Redis URL not configured. Set either REDIS_URL or UPSTASH_REDIS_REST_URL "
        "environment variable."
    )


def get_connection_pool(
    max_connections: int = 50,
    socket_timeout: float = 5.0,
    socket_connect_timeout: float = 5.0,
    retry_on_timeout: bool = True,
    health_check_interval: int = 30,
) -> ConnectionPool:
    """
    Create or return existing Redis connection pool.

    Connection pooling improves performance by reusing connections
    and prevents connection exhaustion under high load.

    Args:
        max_connections: Maximum number of connections in pool (default: 50)
        socket_timeout: Socket timeout in seconds (default: 5.0)
        socket_connect_timeout: Connection timeout in seconds (default: 5.0)
        retry_on_timeout: Whether to retry operations on timeout (default: True)
        health_check_interval: Health check interval in seconds (default: 30)

    Returns:
        ConnectionPool: Redis connection pool instance
    """
    global _redis_pool

    if _redis_pool is None:
        redis_url = _get_redis_url()

        logger.info(
            f"Creating Redis connection pool with max_connections={max_connections}, "
            f"socket_timeout={socket_timeout}s, health_check_interval={health_check_interval}s"
        )

        _redis_pool = ConnectionPool.from_url(
            redis_url,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            retry_on_timeout=retry_on_timeout,
            health_check_interval=health_check_interval,
            decode_responses=True,  # Automatically decode bytes to strings
        )

    return _redis_pool


async def get_redis() -> Redis:
    """
    Get Redis client instance with connection pooling.

    Returns a singleton Redis client that reuses the connection pool
    for optimal performance.

    Returns:
        Redis: Async Redis client instance

    Example:
        redis = await get_redis()
        await redis.set("key", "value", ex=60)
        result = await redis.get("key")
    """
    global _redis_client

    if _redis_client is None:
        pool = get_connection_pool()
        _redis_client = Redis(connection_pool=pool)
        logger.info("Redis client initialized with connection pool")

    return _redis_client


async def close_redis() -> None:
    """
    Close Redis connection pool and client.

    Should be called on application shutdown to clean up resources.

    Example:
        # In FastAPI lifespan
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            yield
            await close_redis()
    """
    global _redis_pool, _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")

    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
        logger.info("Redis connection pool disconnected")


async def redis_health_check(timeout: float = 3.0) -> bool:
    """
    Check Redis connection health.

    Performs a PING operation to verify Redis is reachable and responsive.

    Args:
        timeout: Health check timeout in seconds (default: 3.0)

    Returns:
        bool: True if Redis is healthy, False otherwise

    Example:
        if await redis_health_check():
            print("Redis is healthy")
        else:
            print("Redis is unavailable")
    """
    try:
        client = await get_redis()
        # Set a shorter timeout for health checks
        response = await client.ping()

        if response:
            logger.debug("Redis health check passed")
            return True
        else:
            logger.warning("Redis health check failed: PING returned False")
            return False

    except (RedisConnectionError, RedisTimeoutError) as e:
        logger.error(f"Redis health check failed: {type(e).__name__}: {e}")
        return False
    except RedisError as e:
        logger.error(f"Redis health check error: {type(e).__name__}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during Redis health check: {type(e).__name__}: {e}")
        return False


# =============================================================================
# Helper Functions for Common Operations
# =============================================================================


async def acquire_lock(
    key: str,
    ttl: int = 60,
    value: str = "1",
) -> bool:
    """
    Acquire a distributed lock using Redis SETNX.

    Uses SET with NX (set if not exists) and EX (expiration) flags for
    atomic lock acquisition with automatic expiration.

    Args:
        key: Lock key (e.g., "payment_lock:user@example.com")
        ttl: Lock time-to-live in seconds (default: 60)
        value: Lock value (default: "1")

    Returns:
        bool: True if lock acquired, False if already locked

    Example:
        # Acquire lock for payment processing
        lock_key = f"payment_lock:{normalized_email}"
        if await acquire_lock(lock_key, ttl=60):
            try:
                # Process payment
                pass
            finally:
                await release_lock(lock_key)
        else:
            raise HTTPException(409, "Lock already held")

    Reference:
        research.md lines 460-529 (Redis distributed lock patterns)
    """
    try:
        client = await get_redis()
        # SETNX returns True if key was set, False if already exists
        acquired = await client.set(key, value, nx=True, ex=ttl)

        if acquired:
            logger.debug(f"Lock acquired: {key} (TTL: {ttl}s)")
        else:
            logger.debug(f"Lock already held: {key}")

        return bool(acquired)

    except RedisError as e:
        logger.error(f"Failed to acquire lock {key}: {type(e).__name__}: {e}")
        # Fail open: return False to indicate lock not acquired
        return False


async def release_lock(key: str) -> bool:
    """
    Release a distributed lock by deleting the key.

    Note: Locks will auto-expire via TTL, so explicit release is optional.
    Use this for early release when operation completes before TTL.

    Args:
        key: Lock key to release

    Returns:
        bool: True if lock was released, False otherwise

    Example:
        lock_key = f"payment_lock:{email}"
        await release_lock(lock_key)
    """
    try:
        client = await get_redis()
        deleted = await client.delete(key)

        if deleted:
            logger.debug(f"Lock released: {key}")
            return True
        else:
            logger.debug(f"Lock not found (already expired): {key}")
            return False

    except RedisError as e:
        logger.error(f"Failed to release lock {key}: {type(e).__name__}: {e}")
        return False


async def increment_with_ttl(
    key: str,
    ttl: int = 86400,
    amount: int = 1,
) -> Optional[int]:
    """
    Increment a counter with automatic TTL on first increment.

    Used for rate limiting with daily/hourly reset windows.
    Sets TTL only on first increment (when counter == 1).

    Args:
        key: Counter key (e.g., "download_limit:user:123:2025-01-05")
        ttl: Time-to-live in seconds (default: 86400 = 24 hours)
        amount: Increment amount (default: 1)

    Returns:
        Optional[int]: New counter value, or None on error

    Example:
        # Rate limit: 10 downloads per day
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"download_limit:user:{user_id}:{today}"
        count = await increment_with_ttl(key, ttl=86400)

        if count and count > 10:
            raise HTTPException(429, "Rate limit exceeded")

    Reference:
        research.md lines 1207-1305 (Redis rate limiting implementation)
    """
    try:
        client = await get_redis()

        # Increment counter
        current_count = await client.incr(key, amount)

        # Set TTL only on first increment
        if current_count == amount:
            await client.expire(key, ttl)
            logger.debug(f"Counter initialized: {key} = {current_count} (TTL: {ttl}s)")
        else:
            logger.debug(f"Counter incremented: {key} = {current_count}")

        return current_count

    except RedisError as e:
        logger.error(f"Failed to increment counter {key}: {type(e).__name__}: {e}")
        return None


async def get_counter(key: str) -> Optional[int]:
    """
    Get current counter value.

    Args:
        key: Counter key

    Returns:
        Optional[int]: Counter value, or 0 if key doesn't exist, None on error

    Example:
        count = await get_counter(f"download_limit:user:{user_id}:2025-01-05")
        if count and count >= 10:
            # Rate limit exceeded
            pass
    """
    try:
        client = await get_redis()
        value = await client.get(key)

        if value is None:
            return 0

        return int(value)

    except (ValueError, RedisError) as e:
        logger.error(f"Failed to get counter {key}: {type(e).__name__}: {e}")
        return None


async def set_with_ttl(
    key: str,
    value: Any,
    ttl: int,
) -> bool:
    """
    Set a key with automatic expiration.

    Args:
        key: Cache key
        value: Value to store (will be converted to string)
        ttl: Time-to-live in seconds

    Returns:
        bool: True if set successfully, False otherwise

    Example:
        # Cache verification code for 10 minutes
        await set_with_ttl(f"verify_code:{email}", code, ttl=600)
    """
    try:
        client = await get_redis()
        result = await client.setex(key, ttl, str(value))

        if result:
            logger.debug(f"Key set: {key} (TTL: {ttl}s)")
            return True
        else:
            logger.warning(f"Failed to set key: {key}")
            return False

    except RedisError as e:
        logger.error(f"Failed to set key {key}: {type(e).__name__}: {e}")
        return False


async def get_value(key: str) -> Optional[str]:
    """
    Get a value by key.

    Args:
        key: Key to retrieve

    Returns:
        Optional[str]: Value if exists, None otherwise

    Example:
        code = await get_value(f"verify_code:{email}")
        if code == user_input:
            # Verification successful
            pass
    """
    try:
        client = await get_redis()
        value = await client.get(key)
        return value

    except RedisError as e:
        logger.error(f"Failed to get key {key}: {type(e).__name__}: {e}")
        return None


async def delete_key(key: str) -> bool:
    """
    Delete a key from Redis.

    Args:
        key: Key to delete

    Returns:
        bool: True if key was deleted, False otherwise

    Example:
        # Invalidate verification code after successful use
        await delete_key(f"verify_code:{email}")
    """
    try:
        client = await get_redis()
        deleted = await client.delete(key)

        if deleted:
            logger.debug(f"Key deleted: {key}")
            return True
        else:
            logger.debug(f"Key not found: {key}")
            return False

    except RedisError as e:
        logger.error(f"Failed to delete key {key}: {type(e).__name__}: {e}")
        return False


async def get_ttl(key: str) -> Optional[int]:
    """
    Get remaining time-to-live for a key.

    Args:
        key: Key to check

    Returns:
        Optional[int]: TTL in seconds, -1 if key exists but has no TTL,
                      -2 if key doesn't exist, None on error

    Example:
        ttl = await get_ttl(f"download_limit:user:{user_id}:2025-01-05")
        if ttl and ttl > 0:
            hours_remaining = ttl // 3600
            print(f"Rate limit resets in {hours_remaining} hours")
    """
    try:
        client = await get_redis()
        ttl = await client.ttl(key)
        return ttl

    except RedisError as e:
        logger.error(f"Failed to get TTL for key {key}: {type(e).__name__}: {e}")
        return None


# =============================================================================
# Context Manager for Safe Redis Operations
# =============================================================================


@asynccontextmanager
async def redis_transaction():
    """
    Context manager for Redis operations with automatic error handling.

    Provides a clean interface for executing multiple Redis operations
    with proper error handling and resource cleanup.

    Example:
        async with redis_transaction() as redis:
            await redis.set("key1", "value1")
            await redis.set("key2", "value2")

    Yields:
        Redis: Redis client instance
    """
    client = await get_redis()
    try:
        yield client
    except RedisError as e:
        logger.error(f"Redis transaction error: {type(e).__name__}: {e}")
        raise
    finally:
        # Connection is returned to pool automatically
        pass
