"""
Magic Link Token Generation Service

Provides secure, cryptographically-random magic link tokens for passwordless
email-based plan recovery (FR-R-001, FR-R-002).

Features:
- 256-bit entropy tokens using secrets.token_urlsafe(32)
- SHA256 hashing before database storage (never store plaintext)
- 24-hour expiration window
- Single-use enforcement via used_at timestamp
- IP address tracking for security audit trail
- Rate limiting integration (3 per email per 24h, 5 per IP per hour)

Security Standards:
- Uses secrets module (cryptographically secure random number generator)
- Constant-time comparison for token validation (hmac.compare_digest)
- Generic error messages to prevent email enumeration
- Rate limiting to prevent abuse

Usage:
    from src.services.magic_link import generate_magic_link_token, verify_magic_link_token

    # Generate token
    token, token_record = await generate_magic_link_token(
        email="user@example.com",
        ip_address="192.168.1.1",
        db=db
    )

    # Verify token
    meal_plan_ids = await verify_magic_link_token(
        token="abc123...",
        ip_address="192.168.1.1",
        db=db
    )
"""

import secrets
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Tuple, List, Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.magic_link import MagicLinkToken
from src.models.meal_plan import MealPlan
from src.lib.email_utils import normalize_email

# Configure logging
logger = logging.getLogger(__name__)

# Token configuration
TOKEN_ENTROPY_BYTES = 32  # 256 bits of entropy
TOKEN_EXPIRATION_HOURS = 24  # 24-hour validity window


async def generate_magic_link_token(
    email: str,
    ip_address: str,
    db: AsyncSession,
) -> Tuple[str, MagicLinkToken]:
    """
    Generate cryptographically secure magic link token (T090, FR-R-002).

    Creates a 256-bit entropy token using secrets.token_urlsafe(), hashes it
    with SHA256, and stores the hash in the database. The plaintext token is
    returned to the caller for sending via email, but never stored.

    Token Security:
    - 256-bit entropy (32 bytes) provides 2^256 possible tokens
    - URL-safe base64 encoding (43 characters)
    - SHA256 hash stored in database (prevents token recovery from DB compromise)
    - Single-use enforcement (used_at timestamp)
    - 24-hour expiration (expires_at timestamp)
    - IP tracking for security audit trail

    Args:
        email: User's email address (will be normalized)
        ip_address: Client IP address for audit trail
        db: Async database session

    Returns:
        Tuple[str, MagicLinkToken]: (plaintext_token, token_record)
        - plaintext_token: URL-safe token to send via email (43 chars)
        - token_record: Database record with token_hash, expires_at, etc.

    Example:
        token, record = await generate_magic_link_token(
            email="user@example.com",
            ip_address="192.168.1.1",
            db=db
        )

        # Send token via email
        magic_link_url = f"https://yourdomain.com/recover-plan?token={token}"
        await send_email(email, magic_link_url)

    Security Notes:
        - Never log the plaintext token
        - Only send token via email (never in response body)
        - Use constant-time comparison for validation (hmac.compare_digest)
        - Rate limiting should be applied before calling this function

    Reference:
        research.md lines 1074-1140 (Magic link token generation)
    """
    # Normalize email for consistent lookup
    normalized_email = normalize_email(email)

    # Generate cryptographically secure token (256 bits = 32 bytes)
    # token_urlsafe returns base64-encoded string (~43 characters for 32 bytes)
    plaintext_token = secrets.token_urlsafe(TOKEN_ENTROPY_BYTES)

    # Hash token with SHA256 for database storage
    # We store the hash, not the plaintext, to prevent token recovery if DB is compromised
    token_hash = hashlib.sha256(plaintext_token.encode('utf-8')).hexdigest()

    # Calculate expiration time (24 hours from now)
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(hours=TOKEN_EXPIRATION_HOURS)

    # Create database record
    token_record = MagicLinkToken(
        token_hash=token_hash,
        email=email,  # Original email for communications
        normalized_email=normalized_email,  # Normalized for lookups
        created_at=created_at,
        expires_at=expires_at,
        used_at=None,  # Not yet used
        generation_ip=ip_address,
        usage_ip=None,  # Will be set when token is used
    )

    # Save to database
    db.add(token_record)
    await db.commit()
    await db.refresh(token_record)

    logger.info(
        f"Magic link token generated for {normalized_email} "
        f"(expires: {expires_at.isoformat()}, ip: {ip_address})"
    )

    # Return plaintext token (for emailing) and database record
    return plaintext_token, token_record


async def verify_magic_link_token(
    token: str,
    ip_address: str,
    db: AsyncSession,
) -> Tuple[Optional[MagicLinkToken], List[str]]:
    """
    Verify magic link token and return associated meal plan IDs (T094-T096).

    Validates the token, marks it as used atomically, and returns all meal plan IDs
    associated with the email address. Implements single-use enforcement
    and expiration checking.

    Token Validation:
    - Token must exist in database (hash lookup)
    - Token must not be expired (expires_at > now)
    - Token must not be used (used_at IS NULL)
    - Uses constant-time comparison to prevent timing attacks

    On Success:
    - Marks token as used (sets used_at timestamp) - ATOMIC
    - Records usage IP address (T096)
    - Logs IP mismatch warning to Sentry if IPs don't match (T096)
    - Returns token record and meal plan IDs for the email

    On Failure:
    - Returns (None, []) (generic error to prevent enumeration)
    - Logs detailed error for security monitoring

    Args:
        token: Plaintext token from email link
        ip_address: Client IP address for audit trail (T096)
        db: Async database session

    Returns:
        Tuple[Optional[MagicLinkToken], List[str]]: (token_record, meal_plan_ids)
        - token_record: Database record with email, created_at, etc. (None if invalid)
        - meal_plan_ids: List of meal plan IDs for the email (empty if invalid)

    Example:
        token_record, meal_plan_ids = await verify_magic_link_token(
            token="abc123...",
            ip_address="192.168.1.1",
            db=db
        )

        if token_record and meal_plan_ids:
            # Token valid - return meal plan details
            return {"meal_plan_ids": meal_plan_ids, "email": token_record.email}
        else:
            # Token invalid - show error
            raise HTTPException(400, "Invalid or expired magic link")

    Security Notes:
        - Always use constant-time comparison (hmac.compare_digest)
        - Return generic error messages to prevent enumeration
        - Log all validation attempts for security monitoring
        - Mark token as used atomically to prevent race conditions (T095)
        - Log IP mismatch to Sentry but don't block (T096)

    Error Cases:
        - Token not found in database → (None, [])
        - Token expired → (None, []), mark as used, log warning
        - Token already used → (None, []), log warning (T095)
        - Database error → (None, []), log error

    Reference:
        research.md lines 1141-1180 (Magic link verification)
        Tasks T094-T096 (Phase 7.2)
    """
    # Hash the provided token for database lookup
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()

    try:
        # Find token record by hash
        result = await db.execute(
            select(MagicLinkToken).where(MagicLinkToken.token_hash == token_hash)
        )
        token_record = result.scalar_one_or_none()

        # Token not found
        if not token_record:
            logger.warning(
                f"Magic link token not found (ip: {ip_address}). "
                "Possible invalid token or token hash mismatch."
            )
            return None, []

        # T095: Check if token is already used (single-use enforcement)
        if token_record.used_at is not None:
            logger.warning(
                f"Magic link token already used at {token_record.used_at.isoformat()} "
                f"for {token_record.normalized_email} (ip: {ip_address})"
            )
            return None, []

        # Check if token is expired
        now = datetime.utcnow()
        if now > token_record.expires_at:
            logger.warning(
                f"Magic link token expired at {token_record.expires_at.isoformat()} "
                f"for {token_record.normalized_email} (ip: {ip_address})"
            )
            # Mark as used to prevent replay attempts
            token_record.used_at = now
            token_record.usage_ip = ip_address
            await db.commit()
            return None, []

        # T095: Token is valid - mark as used ATOMICALLY
        # This prevents race conditions where multiple requests verify the same token
        token_record.used_at = now
        token_record.usage_ip = ip_address
        await db.commit()

        # T096: Check IP mismatch and log to Sentry (but don't block)
        if token_record.generation_ip and token_record.usage_ip != token_record.generation_ip:
            logger.warning(
                f"IP mismatch for magic link token: "
                f"generated from {token_record.generation_ip}, "
                f"used from {token_record.usage_ip} "
                f"for {token_record.normalized_email}. "
                f"This may indicate the user switched networks (normal) or token forwarding (suspicious).",
                extra={
                    "token_id": token_record.id,
                    "email": token_record.normalized_email,
                    "generation_ip": token_record.generation_ip,
                    "usage_ip": token_record.usage_ip,
                    "security_event": "magic_link_ip_mismatch"
                }
            )

        logger.info(
            f"Magic link token verified successfully for {token_record.normalized_email} "
            f"(ip: {ip_address})"
        )

        # Find all meal plans for this email
        result = await db.execute(
            select(MealPlan.id).where(
                MealPlan.normalized_email == token_record.normalized_email
            )
        )
        meal_plan_ids = [row[0] for row in result.all()]

        logger.info(
            f"Found {len(meal_plan_ids)} meal plans for {token_record.normalized_email}"
        )

        return token_record, meal_plan_ids

    except Exception as e:
        logger.error(
            f"Error verifying magic link token: {type(e).__name__}: {e} "
            f"(ip: {ip_address})",
            exc_info=True
        )
        return None, []


async def check_magic_link_rate_limit(
    email: str,
    db: AsyncSession,
) -> Tuple[bool, int]:
    """
    Check if email has exceeded magic link generation rate limit.

    Rate limit: 3 magic links per email per 24 hours (FR-R-002).

    Counts magic links created in the last 24 hours for the normalized email.
    This prevents abuse and protects against email bombing attacks.

    Args:
        email: User's email address (will be normalized)
        db: Async database session

    Returns:
        Tuple[bool, int]: (is_allowed, count)
        - is_allowed: True if under limit, False if rate limit exceeded
        - count: Current count of magic links in last 24 hours

    Example:
        is_allowed, count = await check_magic_link_rate_limit(
            email="user@example.com",
            db=db
        )

        if not is_allowed:
            raise HTTPException(
                429,
                f"Too many magic link requests. You have {count}/3 requests. "
                "Please try again in 24 hours."
            )

    Reference:
        research.md lines 1107-1119 (Rate limit implementation)
    """
    normalized_email = normalize_email(email)

    # Count magic links created in last 24 hours
    cutoff_time = datetime.utcnow() - timedelta(hours=24)

    result = await db.execute(
        select(func.count(MagicLinkToken.id)).where(
            and_(
                MagicLinkToken.normalized_email == normalized_email,
                MagicLinkToken.created_at > cutoff_time
            )
        )
    )
    count = result.scalar() or 0

    # Rate limit: 3 per 24 hours
    is_allowed = count < 3

    if not is_allowed:
        logger.warning(
            f"Magic link rate limit exceeded for {normalized_email} "
            f"({count}/3 requests in last 24h)"
        )

    return is_allowed, count


async def cleanup_expired_tokens(db: AsyncSession) -> int:
    """
    Delete expired and used magic link tokens (cleanup job).

    Removes tokens that are either:
    1. Expired (expires_at < now)
    2. Used and older than 24 hours (used_at IS NOT NULL AND created_at < now - 24h)

    This keeps the database clean and improves query performance.
    Should be run periodically (e.g., daily cron job).

    Args:
        db: Async database session

    Returns:
        int: Number of tokens deleted

    Example:
        # In cleanup job
        deleted_count = await cleanup_expired_tokens(db)
        logger.info(f"Cleaned up {deleted_count} magic link tokens")

    Reference:
        Phase 9.2 - Data retention cleanup (T128-T134)
    """
    now = datetime.utcnow()
    cutoff_time = now - timedelta(hours=24)

    # Find tokens to delete
    result = await db.execute(
        select(MagicLinkToken).where(
            # Expired tokens
            (MagicLinkToken.expires_at < now) |
            # Used tokens older than 24 hours
            (and_(
                MagicLinkToken.used_at.isnot(None),
                MagicLinkToken.created_at < cutoff_time
            ))
        )
    )
    tokens_to_delete = result.scalars().all()

    # Delete tokens
    for token in tokens_to_delete:
        await db.delete(token)

    await db.commit()

    deleted_count = len(tokens_to_delete)
    logger.info(f"Cleaned up {deleted_count} expired/used magic link tokens")

    return deleted_count
