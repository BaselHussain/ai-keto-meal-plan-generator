"""
Email verification code generator and validator.

This service implements secure email verification with 6-digit codes and
24-hour verified status validity as specified in FR-Q-019.

Features:
- Cryptographically secure 6-digit code generation
- 10-minute code expiry
- 24-hour verified status validity (survives Paddle modal abandonment)
- 60-second resend cooldown
- Redis-based storage
- Auth-aware logic (skip verification for authenticated users)

Redis Key Structure:
- verification_code:{normalized_email} - 6-digit code, 10-min TTL
- verification_verified:{normalized_email} - timestamp, 24-hour TTL
- verification_cooldown:{normalized_email} - cooldown tracker, 60s TTL

Security:
- Uses secrets module for cryptographically secure code generation
- Constant-time comparison for code validation (prevent timing attacks)
- Email normalization applied consistently (Gmail dot/plus removal)
- Rate limiting via cooldown mechanism

Usage:
    from src.services.email_verification import (
        send_verification_code,
        verify_code,
        is_email_verified,
    )

    # Send verification code
    result = await send_verification_code("user@example.com")
    if not result["success"]:
        print(result["error"])

    # Verify code
    result = await verify_code("user@example.com", "123456")
    if result["success"]:
        print("Email verified for 24 hours")

    # Check if email is verified
    verified = await is_email_verified("user@example.com")
"""

import secrets
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from hmac import compare_digest

from src.lib.redis_client import (
    get_redis,
    set_with_ttl,
    get_value,
    delete_key,
    get_ttl,
)
from src.lib.email_utils import normalize_email
from src.services.email_service import send_verification_email

# Configure logging
logger = logging.getLogger(__name__)

# Constants from FR-Q-019
CODE_LENGTH = 6
CODE_EXPIRY_SECONDS = 600  # 10 minutes
VERIFIED_STATUS_SECONDS = 86400  # 24 hours
RESEND_COOLDOWN_SECONDS = 60  # 60 seconds


def generate_verification_code() -> str:
    """
    Generate a cryptographically secure 6-digit verification code.

    Uses secrets.choice() to ensure cryptographic randomness, which is
    required for security-sensitive applications. This is more secure than
    random.randint() which uses a pseudo-random number generator.

    Returns:
        str: 6-digit code (e.g., "123456")

    Example:
        code = generate_verification_code()
        # Returns: "842719" (example, will vary)
    """
    # Use secrets.choice() for cryptographically secure random selection
    # This is equivalent to secrets.randbelow() but more readable
    digits = "0123456789"
    code = "".join(secrets.choice(digits) for _ in range(CODE_LENGTH))

    logger.debug(f"Generated verification code (length: {CODE_LENGTH})")
    return code


def _get_redis_key(email: str, key_type: str) -> str:
    """
    Generate Redis key for email verification data.

    Args:
        email: Email address (will be normalized)
        key_type: One of: "code", "verified", "cooldown"

    Returns:
        str: Redis key (e.g., "verification_code:user@example.com")
    """
    normalized = normalize_email(email)
    return f"verification_{key_type}:{normalized}"


async def send_verification_code(email: str) -> Dict[str, Any]:
    """
    Generate and store verification code with cooldown enforcement.

    This function:
    1. Normalizes email address (Gmail dot/plus removal)
    2. Checks if email is already verified (24h status)
    3. Enforces 60-second cooldown between sends
    4. Generates cryptographically secure 6-digit code
    5. Stores code in Redis with 10-minute TTL
    6. Sets cooldown flag for 60 seconds

    Args:
        email: Email address to send verification code to

    Returns:
        Dict with keys:
        - success (bool): True if code was sent
        - code (str): The 6-digit code (for development/testing)
        - error (str): Error message if success is False
        - cooldown_remaining (int): Seconds until next send allowed

    Examples:
        >>> result = await send_verification_code("user@example.com")
        >>> if result["success"]:
        ...     print(f"Code sent: {result['code']}")
        ... else:
        ...     print(f"Error: {result['error']}")

    Error Cases:
        - Email already verified: {"success": False, "error": "Email already verified"}
        - Cooldown active: {"success": False, "error": "Please wait...", "cooldown_remaining": 45}
        - Redis error: {"success": False, "error": "Failed to send verification code"}
    """
    try:
        # Normalize email
        normalized_email = normalize_email(email)

        # Check if email is already verified (24h status)
        if await is_email_verified(email):
            logger.info(f"Email already verified: {normalized_email}")
            return {
                "success": False,
                "error": "Email already verified for the next 24 hours",
            }

        # Check cooldown
        cooldown_key = _get_redis_key(email, "cooldown")
        cooldown_ttl = await get_ttl(cooldown_key)

        if cooldown_ttl and cooldown_ttl > 0:
            logger.info(
                f"Cooldown active for {normalized_email}: {cooldown_ttl}s remaining"
            )
            return {
                "success": False,
                "error": f"Please wait {cooldown_ttl} seconds before requesting a new code",
                "cooldown_remaining": cooldown_ttl,
            }

        # Generate cryptographically secure code
        code = generate_verification_code()

        # Store code in Redis with 10-minute expiry
        code_key = _get_redis_key(email, "code")
        code_stored = await set_with_ttl(code_key, code, CODE_EXPIRY_SECONDS)

        if not code_stored:
            logger.error(f"Failed to store verification code for {normalized_email}")
            return {
                "success": False,
                "error": "Failed to send verification code. Please try again.",
            }

        # Set cooldown flag (60 seconds)
        await set_with_ttl(cooldown_key, "1", RESEND_COOLDOWN_SECONDS)

        logger.info(
            f"Verification code generated for {normalized_email} "
            f"(expires in {CODE_EXPIRY_SECONDS}s)"
        )

        # Send verification email via Resend
        email_result = await send_verification_email(
            to_email=email,  # Use original email (not normalized) for sending
            verification_code=code
        )

        if not email_result["success"]:
            # Email sending failed - log error and return failure
            logger.error(
                f"Failed to send verification email to {normalized_email}: "
                f"{email_result.get('error', 'Unknown error')}"
            )
            return {
                "success": False,
                "error": "Failed to send verification email. Please try again.",
            }

        logger.info(
            f"Verification email sent successfully to {normalized_email} "
            f"(message_id: {email_result.get('message_id', 'unknown')}, "
            f"attempts: {email_result.get('attempts', 1)})"
        )

        return {
            "success": True,
            "message": f"Verification code sent to your email (expires in {CODE_EXPIRY_SECONDS // 60} minutes)",
        }

    except ValueError as e:
        # Email normalization error
        logger.warning(f"Invalid email format: {email} - {e}")
        return {
            "success": False,
            "error": f"Invalid email format: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Unexpected error sending verification code: {type(e).__name__}: {e}")
        return {
            "success": False,
            "error": "Failed to send verification code. Please try again.",
        }


async def verify_code(email: str, code: str) -> Dict[str, Any]:
    """
    Validate verification code and mark email as verified for 24 hours.

    This function:
    1. Normalizes email address
    2. Retrieves stored code from Redis
    3. Uses constant-time comparison to prevent timing attacks
    4. If valid, marks email as verified for 24 hours
    5. Deletes the used code (one-time use)

    Args:
        email: Email address to verify
        code: 6-digit verification code from user input

    Returns:
        Dict with keys:
        - success (bool): True if verification succeeded
        - message (str): Success message
        - error (str): Error message if success is False

    Examples:
        >>> result = await verify_code("user@example.com", "123456")
        >>> if result["success"]:
        ...     print("Email verified!")

    Error Cases:
        - Code expired/not found: {"success": False, "error": "Verification code expired..."}
        - Code mismatch: {"success": False, "error": "Invalid verification code"}
        - Redis error: {"success": False, "error": "Verification failed..."}

    Security:
        Uses constant-time comparison (hmac.compare_digest) to prevent timing
        attacks that could leak information about the correct code.
    """
    try:
        # Normalize email
        normalized_email = normalize_email(email)

        # Retrieve stored code from Redis
        code_key = _get_redis_key(email, "code")
        stored_code = await get_value(code_key)

        if not stored_code:
            logger.warning(f"No verification code found for {normalized_email}")
            return {
                "success": False,
                "error": "Verification code expired or not found. Please request a new code.",
            }

        # Constant-time comparison to prevent timing attacks
        # This ensures the comparison takes the same time regardless of how many
        # characters match, preventing attackers from guessing the code character-by-character
        if not compare_digest(stored_code, code.strip()):
            logger.warning(f"Invalid verification code for {normalized_email}")
            return {
                "success": False,
                "error": "Invalid verification code. Please check and try again.",
            }

        # Code is valid - mark email as verified for 24 hours
        verified_key = _get_redis_key(email, "verified")
        timestamp = datetime.utcnow().isoformat()
        verified_stored = await set_with_ttl(
            verified_key, timestamp, VERIFIED_STATUS_SECONDS
        )

        if not verified_stored:
            logger.error(f"Failed to store verified status for {normalized_email}")
            return {
                "success": False,
                "error": "Verification failed. Please try again.",
            }

        # Delete used code (one-time use)
        await delete_key(code_key)

        # Clear cooldown (user successfully verified)
        cooldown_key = _get_redis_key(email, "cooldown")
        await delete_key(cooldown_key)

        logger.info(
            f"Email verified: {normalized_email} "
            f"(valid for {VERIFIED_STATUS_SECONDS // 3600} hours)"
        )

        return {
            "success": True,
            "message": f"Email verified successfully. Valid for {VERIFIED_STATUS_SECONDS // 3600} hours.",
        }

    except ValueError as e:
        # Email normalization error
        logger.warning(f"Invalid email format: {email} - {e}")
        return {
            "success": False,
            "error": f"Invalid email format: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Unexpected error during verification: {type(e).__name__}: {e}")
        return {
            "success": False,
            "error": "Verification failed. Please try again.",
        }


async def is_email_verified(email: str) -> bool:
    """
    Check if email has valid 24-hour verified status.

    This status persists even if the user abandons the Paddle payment modal
    and returns later, as specified in FR-Q-019.

    Args:
        email: Email address to check

    Returns:
        bool: True if email is verified (within 24-hour window), False otherwise

    Examples:
        >>> verified = await is_email_verified("user@example.com")
        >>> if verified:
        ...     print("Email is verified, proceed to payment")
        ... else:
        ...     print("Email verification required")

    Notes:
        Returns False on any error (fail-safe behavior).
        Authenticated users should skip verification entirely at the API level.
    """
    try:
        # Normalize email
        normalized_email = normalize_email(email)

        # Check if verified status exists in Redis
        verified_key = _get_redis_key(email, "verified")
        verified_status = await get_value(verified_key)

        if verified_status:
            logger.debug(f"Email verified status found: {normalized_email}")
            return True
        else:
            logger.debug(f"Email not verified: {normalized_email}")
            return False

    except ValueError as e:
        # Email normalization error
        logger.warning(f"Invalid email format during verification check: {email} - {e}")
        return False
    except Exception as e:
        logger.error(
            f"Error checking verification status: {type(e).__name__}: {e}"
        )
        return False


async def clear_verification(email: str) -> Dict[str, Any]:
    """
    Clear all verification data for an email (testing/admin use).

    Deletes:
    - Verification code (if any)
    - Verified status (if any)
    - Cooldown flag (if any)

    Args:
        email: Email address to clear verification data for

    Returns:
        Dict with keys:
        - success (bool): True if data was cleared
        - cleared (list): List of cleared keys
        - message (str): Status message

    Examples:
        >>> result = await clear_verification("user@example.com")
        >>> print(result["cleared"])
        ['verification_code:user@example.com', 'verification_verified:user@example.com']

    Use Cases:
        - Testing: Reset verification state between tests
        - Admin: Clear stuck verification states
        - User request: Remove verification data
    """
    try:
        # Normalize email
        normalized_email = normalize_email(email)

        # Delete all verification-related keys
        code_key = _get_redis_key(email, "code")
        verified_key = _get_redis_key(email, "verified")
        cooldown_key = _get_redis_key(email, "cooldown")

        cleared_keys = []

        for key in [code_key, verified_key, cooldown_key]:
            deleted = await delete_key(key)
            if deleted:
                cleared_keys.append(key)

        logger.info(
            f"Cleared verification data for {normalized_email}: {len(cleared_keys)} keys deleted"
        )

        return {
            "success": True,
            "cleared": cleared_keys,
            "message": f"Cleared {len(cleared_keys)} verification keys for {normalized_email}",
        }

    except ValueError as e:
        # Email normalization error
        logger.warning(f"Invalid email format: {email} - {e}")
        return {
            "success": False,
            "error": f"Invalid email format: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Error clearing verification data: {type(e).__name__}: {e}")
        return {
            "success": False,
            "error": "Failed to clear verification data.",
        }


async def get_verification_status(email: str) -> Dict[str, Any]:
    """
    Get detailed verification status for debugging/admin purposes.

    Returns:
        Dict with keys:
        - email (str): Normalized email
        - has_code (bool): Whether active code exists
        - code_ttl (int): Seconds until code expires (-2 if no code)
        - is_verified (bool): Whether email has verified status
        - verified_ttl (int): Seconds until verified status expires (-2 if not verified)
        - is_cooldown_active (bool): Whether cooldown is active
        - cooldown_ttl (int): Seconds until cooldown expires (-2 if no cooldown)

    Examples:
        >>> status = await get_verification_status("user@example.com")
        >>> print(f"Code TTL: {status['code_ttl']}s")
        >>> print(f"Verified: {status['is_verified']}")
    """
    try:
        # Normalize email
        normalized_email = normalize_email(email)

        # Get code status
        code_key = _get_redis_key(email, "code")
        code_ttl = await get_ttl(code_key)
        has_code = code_ttl is not None and code_ttl > 0

        # Get verified status
        verified_key = _get_redis_key(email, "verified")
        verified_ttl = await get_ttl(verified_key)
        is_verified = verified_ttl is not None and verified_ttl > 0

        # Get cooldown status
        cooldown_key = _get_redis_key(email, "cooldown")
        cooldown_ttl = await get_ttl(cooldown_key)
        is_cooldown_active = cooldown_ttl is not None and cooldown_ttl > 0

        return {
            "email": normalized_email,
            "has_code": has_code,
            "code_ttl": code_ttl if code_ttl else -2,
            "is_verified": is_verified,
            "verified_ttl": verified_ttl if verified_ttl else -2,
            "is_cooldown_active": is_cooldown_active,
            "cooldown_ttl": cooldown_ttl if cooldown_ttl else -2,
        }

    except ValueError as e:
        # Email normalization error
        logger.warning(f"Invalid email format: {email} - {e}")
        return {
            "error": f"Invalid email format: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Error getting verification status: {type(e).__name__}: {e}")
        return {
            "error": "Failed to retrieve verification status",
        }
