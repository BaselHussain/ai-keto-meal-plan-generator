"""
Rate Limiting Utilities using Redis

Provides rate limiting functionality for API endpoints to prevent abuse
and protect against DDoS attacks. Uses Redis for distributed rate limiting
across multiple server instances.

Features:
- IP-based rate limiting (requests per IP per time window)
- Email-based rate limiting (requests per email per time window)
- Configurable time windows and limits
- Automatic key expiration via Redis TTL
- Thread-safe with atomic operations (INCR + EXPIRE)

Common Use Cases:
- Magic link generation: 3 per email per 24h, 5 per IP per hour
- Email verification: 5 per email per hour, 10 per IP per hour
- API endpoints: 100 per IP per minute

Usage:
    from src.lib.rate_limiting import (
        check_rate_limit_email,
        check_rate_limit_ip,
        RateLimitExceeded
    )

    # Check email rate limit
    try:
        await check_rate_limit_email(
            email="user@example.com",
            limit=3,
            window_seconds=86400,  # 24 hours
            operation="magic_link"
        )
    except RateLimitExceeded as e:
        raise HTTPException(429, str(e))

    # Check IP rate limit
    try:
        await check_rate_limit_ip(
            ip_address="192.168.1.1",
            limit=5,
            window_seconds=3600,  # 1 hour
            operation="magic_link"
        )
    except RateLimitExceeded as e:
        raise HTTPException(429, str(e))
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

from src.lib.redis_client import get_redis, increment_with_ttl
from src.lib.email_utils import normalize_email

# Configure logging
logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """
    Exception raised when rate limit is exceeded.

    Contains information about the limit, current count, and reset time.
    """

    def __init__(
        self,
        message: str,
        limit: int,
        current_count: int,
        reset_time: Optional[datetime] = None,
    ):
        self.message = message
        self.limit = limit
        self.current_count = current_count
        self.reset_time = reset_time
        super().__init__(message)

    def __str__(self):
        return self.message


async def check_rate_limit_email(
    email: str,
    limit: int,
    window_seconds: int,
    operation: str = "request",
) -> None:
    """
    Check rate limit for email address.

    Uses Redis counter with TTL to track requests per email per time window.
    Raises RateLimitExceeded if limit is exceeded.

    Rate Limit Key Format:
        rate_limit:email:{operation}:{normalized_email}

    Args:
        email: Email address to check (will be normalized)
        limit: Maximum requests allowed in time window
        window_seconds: Time window in seconds (e.g., 86400 for 24 hours)
        operation: Operation name for key namespacing (e.g., "magic_link")

    Raises:
        RateLimitExceeded: If limit is exceeded

    Example:
        # Magic link: 3 per email per 24 hours
        await check_rate_limit_email(
            email="user@example.com",
            limit=3,
            window_seconds=86400,
            operation="magic_link"
        )

    Redis Behavior:
        - First request: Creates key with count=1, sets TTL
        - Subsequent requests: Increments counter
        - After window_seconds: Key expires, counter resets to 0
        - Atomic operations prevent race conditions

    Reference:
        research.md lines 1207-1305 (Redis rate limiting)
    """
    normalized_email = normalize_email(email)

    # Build Redis key
    key = f"rate_limit:email:{operation}:{normalized_email}"

    # Increment counter with TTL
    count = await increment_with_ttl(key, ttl=window_seconds, amount=1)

    if count is None:
        # Redis error - fail open (allow request)
        logger.error(
            f"Failed to check email rate limit for {normalized_email} - Redis unavailable"
        )
        return

    # Check if limit exceeded
    if count > limit:
        # Calculate reset time
        from src.lib.redis_client import get_ttl
        ttl = await get_ttl(key)
        reset_time = None
        if ttl and ttl > 0:
            reset_time = datetime.utcnow() + timedelta(seconds=ttl)

        logger.warning(
            f"Rate limit exceeded for email {normalized_email} "
            f"({count}/{limit} {operation} requests in {window_seconds}s window)"
        )

        raise RateLimitExceeded(
            message=(
                f"Too many {operation} requests. "
                f"You have made {count}/{limit} requests. "
                f"Please try again later."
            ),
            limit=limit,
            current_count=count,
            reset_time=reset_time,
        )

    logger.debug(
        f"Email rate limit check passed for {normalized_email} "
        f"({count}/{limit} {operation} requests)"
    )


async def check_rate_limit_ip(
    ip_address: str,
    limit: int,
    window_seconds: int,
    operation: str = "request",
) -> None:
    """
    Check rate limit for IP address.

    Uses Redis counter with TTL to track requests per IP per time window.
    Raises RateLimitExceeded if limit is exceeded.

    Rate Limit Key Format:
        rate_limit:ip:{operation}:{ip_address}

    Args:
        ip_address: Client IP address (IPv4 or IPv6)
        limit: Maximum requests allowed in time window
        window_seconds: Time window in seconds (e.g., 3600 for 1 hour)
        operation: Operation name for key namespacing (e.g., "magic_link")

    Raises:
        RateLimitExceeded: If limit is exceeded

    Example:
        # Magic link: 5 per IP per hour
        await check_rate_limit_ip(
            ip_address="192.168.1.1",
            limit=5,
            window_seconds=3600,
            operation="magic_link"
        )

    Redis Behavior:
        - First request: Creates key with count=1, sets TTL
        - Subsequent requests: Increments counter
        - After window_seconds: Key expires, counter resets to 0
        - Atomic operations prevent race conditions

    Security Notes:
        - IP-based rate limiting can be bypassed with proxies/VPNs
        - Combine with email-based rate limiting for better protection
        - Consider using X-Forwarded-For header with caution (can be spoofed)

    Reference:
        research.md lines 1207-1305 (Redis rate limiting)
    """
    # Build Redis key (sanitize IP to prevent injection)
    sanitized_ip = ip_address.replace(":", "_").replace(".", "_")
    key = f"rate_limit:ip:{operation}:{sanitized_ip}"

    # Increment counter with TTL
    count = await increment_with_ttl(key, ttl=window_seconds, amount=1)

    if count is None:
        # Redis error - fail open (allow request)
        logger.error(
            f"Failed to check IP rate limit for {ip_address} - Redis unavailable"
        )
        return

    # Check if limit exceeded
    if count > limit:
        # Calculate reset time
        from src.lib.redis_client import get_ttl
        ttl = await get_ttl(key)
        reset_time = None
        if ttl and ttl > 0:
            reset_time = datetime.utcnow() + timedelta(seconds=ttl)

        logger.warning(
            f"Rate limit exceeded for IP {ip_address} "
            f"({count}/{limit} {operation} requests in {window_seconds}s window)"
        )

        raise RateLimitExceeded(
            message=(
                f"Too many {operation} requests from your IP address. "
                f"Please try again later."
            ),
            limit=limit,
            current_count=count,
            reset_time=reset_time,
        )

    logger.debug(
        f"IP rate limit check passed for {ip_address} "
        f"({count}/{limit} {operation} requests)"
    )


async def get_rate_limit_status_email(
    email: str,
    operation: str = "request",
) -> dict:
    """
    Get current rate limit status for email.

    Returns information about current usage without incrementing the counter.
    Useful for displaying rate limit info to users.

    Args:
        email: Email address (will be normalized)
        operation: Operation name

    Returns:
        dict: Rate limit status with keys:
        - count: Current request count
        - ttl: Time until reset in seconds (None if no limit)
        - reset_time: Datetime when limit resets (None if no limit)

    Example:
        status = await get_rate_limit_status_email(
            email="user@example.com",
            operation="magic_link"
        )
        print(f"Requests: {status['count']}, Resets in: {status['ttl']}s")
    """
    from src.lib.redis_client import get_counter, get_ttl

    normalized_email = normalize_email(email)
    key = f"rate_limit:email:{operation}:{normalized_email}"

    count = await get_counter(key) or 0
    ttl = await get_ttl(key)

    reset_time = None
    if ttl and ttl > 0:
        reset_time = datetime.utcnow() + timedelta(seconds=ttl)

    return {
        "count": count,
        "ttl": ttl,
        "reset_time": reset_time,
    }


async def get_rate_limit_status_ip(
    ip_address: str,
    operation: str = "request",
) -> dict:
    """
    Get current rate limit status for IP address.

    Returns information about current usage without incrementing the counter.
    Useful for displaying rate limit info to users.

    Args:
        ip_address: Client IP address
        operation: Operation name

    Returns:
        dict: Rate limit status with keys:
        - count: Current request count
        - ttl: Time until reset in seconds (None if no limit)
        - reset_time: Datetime when limit resets (None if no limit)

    Example:
        status = await get_rate_limit_status_ip(
            ip_address="192.168.1.1",
            operation="magic_link"
        )
        print(f"Requests: {status['count']}, Resets in: {status['ttl']}s")
    """
    from src.lib.redis_client import get_counter, get_ttl

    sanitized_ip = ip_address.replace(":", "_").replace(".", "_")
    key = f"rate_limit:ip:{operation}:{sanitized_ip}"

    count = await get_counter(key) or 0
    ttl = await get_ttl(key)

    reset_time = None
    if ttl and ttl > 0:
        reset_time = datetime.utcnow() + timedelta(seconds=ttl)

    return {
        "count": count,
        "ttl": ttl,
        "reset_time": reset_time,
    }


async def reset_rate_limit_email(email: str, operation: str = "request") -> bool:
    """
    Reset rate limit counter for email.

    Deletes the Redis key to allow immediate retry. Use with caution.
    Intended for admin operations or error recovery.

    Args:
        email: Email address (will be normalized)
        operation: Operation name

    Returns:
        bool: True if counter was reset, False otherwise

    Example:
        # Admin endpoint to reset rate limit
        await reset_rate_limit_email(
            email="user@example.com",
            operation="magic_link"
        )
    """
    from src.lib.redis_client import delete_key

    normalized_email = normalize_email(email)
    key = f"rate_limit:email:{operation}:{normalized_email}"

    deleted = await delete_key(key)

    if deleted:
        logger.info(f"Reset rate limit for email {normalized_email} ({operation})")
    else:
        logger.debug(f"No rate limit to reset for email {normalized_email} ({operation})")

    return deleted


async def reset_rate_limit_ip(ip_address: str, operation: str = "request") -> bool:
    """
    Reset rate limit counter for IP address.

    Deletes the Redis key to allow immediate retry. Use with caution.
    Intended for admin operations or error recovery.

    Args:
        ip_address: Client IP address
        operation: Operation name

    Returns:
        bool: True if counter was reset, False otherwise

    Example:
        # Admin endpoint to reset rate limit
        await reset_rate_limit_ip(
            ip_address="192.168.1.1",
            operation="magic_link"
        )
    """
    from src.lib.redis_client import delete_key

    sanitized_ip = ip_address.replace(":", "_").replace(".", "_")
    key = f"rate_limit:ip:{operation}:{sanitized_ip}"

    deleted = await delete_key(key)

    if deleted:
        logger.info(f"Reset rate limit for IP {ip_address} ({operation})")
    else:
        logger.debug(f"No rate limit to reset for IP {ip_address} ({operation})")

    return deleted


async def check_download_rate_limit(
    user_id: Optional[str],
    email: str,
    ip_address: str,
    email_sent_at: Optional[datetime],
    limit: int = 10,
    window_seconds: int = 86400,
) -> None:
    """
    Check download rate limit for PDF downloads (T105, FR-R-005).

    Implements composite rate limiting based on user authentication status:
    - Authenticated users: Rate limited by user_id
    - Magic link users: Rate limited by email+IP hash

    Grace Period (T106):
    - Downloads within 5 minutes of email_sent_at are excluded from rate limiting
    - Allows users to download immediately after purchase without counting toward limit
    - Grace period only applies if email_sent_at is set

    Rate Limit:
    - 10 downloads per 24 hours (configurable)
    - Counter resets after 24 hours (automatic via Redis TTL)

    Redis Key Format:
        download_rate:user:{user_id}  (for authenticated users)
        download_rate:guest:{sha256_hash}  (for magic link users, email+IP hash)

    Args:
        user_id: User ID if authenticated (None for magic link users)
        email: Email address (normalized for magic link users)
        ip_address: Client IP address
        email_sent_at: Email delivery timestamp (None if not yet sent)
        limit: Maximum downloads in window (default: 10)
        window_seconds: Time window in seconds (default: 86400 = 24 hours)

    Raises:
        RateLimitExceeded: If download limit exceeded

    Example:
        # Authenticated user download
        await check_download_rate_limit(
            user_id="user123",
            email="user@example.com",
            ip_address="192.168.1.1",
            email_sent_at=meal_plan.email_sent_at,
        )

        # Magic link user download
        await check_download_rate_limit(
            user_id=None,
            email="user@example.com",
            ip_address="192.168.1.1",
            email_sent_at=meal_plan.email_sent_at,
        )

    Reference:
        research.md lines 1207-1305 (Download rate limiting)
        Tasks T105, T106 (Phase 7.5)
    """
    # T106: Grace period check - first 5 minutes after email delivery
    if email_sent_at:
        time_since_email = datetime.utcnow() - email_sent_at
        grace_period = timedelta(minutes=5)

        if time_since_email < grace_period:
            logger.debug(
                f"Download within grace period ({time_since_email.total_seconds():.0f}s), "
                f"bypassing rate limit"
            )
            return  # Allow without counting

    # T105: Determine identifier based on authentication status
    if user_id:
        # Authenticated user: rate limit by user_id
        identifier = f"user:{user_id}"
    else:
        # Magic link user: rate limit by email+IP hash
        normalized_email = normalize_email(email)
        combined = f"{normalized_email}:{ip_address}"
        hash_value = hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16]
        identifier = f"guest:{hash_value}"

    # Build Redis key
    key = f"download_rate:{identifier}"

    # Increment counter with TTL
    count = await increment_with_ttl(key, ttl=window_seconds, amount=1)

    if count is None:
        # Redis error - fail open (allow download)
        logger.error(
            f"Failed to check download rate limit for {identifier} - Redis unavailable"
        )
        return

    # Check if limit exceeded
    if count > limit:
        # Calculate reset time
        from src.lib.redis_client import get_ttl
        ttl = await get_ttl(key)
        reset_time = None
        if ttl and ttl > 0:
            reset_time = datetime.utcnow() + timedelta(seconds=ttl)

        # Calculate hours until reset for user-friendly message
        hours_until_reset = ttl // 3600 if ttl and ttl > 0 else 24

        logger.warning(
            f"Download rate limit exceeded for {identifier} "
            f"({count}/{limit} downloads in {window_seconds}s window)"
        )

        raise RateLimitExceeded(
            message=(
                f"Download limit reached. You have made {count}/{limit} downloads. "
                f"Please try again in {hours_until_reset} hours."
            ),
            limit=limit,
            current_count=count,
            reset_time=reset_time,
        )

    logger.debug(
        f"Download rate limit check passed for {identifier} "
        f"({count}/{limit} downloads)"
    )
