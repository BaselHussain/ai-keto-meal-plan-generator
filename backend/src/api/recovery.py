"""
Recovery API Endpoints

Provides magic link-based plan recovery functionality for users who have
lost access to their meal plans. Implements passwordless authentication
via secure, time-limited, single-use tokens sent via email.

Endpoints:
- POST /recovery/request-magic-link - Request magic link for plan recovery
- GET /recovery/verify-magic-link - Verify magic link token

Security Features:
- Rate limiting: 3 per email per 24h, 5 per IP per hour
- 256-bit entropy tokens (cryptographically secure)
- SHA256 hashing before database storage
- 24-hour expiration, single-use enforcement
- Generic responses to prevent email enumeration
- IP address logging for security audit trail

Functional Requirements:
- FR-R-001: Optional account creation for permanent access
- FR-R-002: Magic link generation and validation
- FR-E-007: Recovery page with email input

Reference:
    specs/001-keto-meal-plan-generator/contracts/recovery-api.yaml
    Phase 7.1 - Magic link generation (T090-T093)
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.lib.database import get_db
from src.lib.rate_limiting import check_rate_limit_email, check_rate_limit_ip, RateLimitExceeded
from src.schemas.recovery import (
    RecoverPlanRequest,
    RecoverPlanResponse,
    MagicLinkVerifyResponse,
    MagicLinkVerifyErrorResponse,
)
from src.services.magic_link import generate_magic_link_token, verify_magic_link_token
from src.services.email_service import send_magic_link_email
from src.models.meal_plan import MealPlan

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/recovery", tags=["Recovery"])

# App URL from environment
APP_URL = os.getenv("APP_URL", "http://localhost:3000")


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.

    Handles both direct connections and proxied connections (X-Forwarded-For).
    For security, we prefer the direct connection IP to prevent spoofing.

    Args:
        request: FastAPI request object

    Returns:
        str: Client IP address (IPv4 or IPv6)
    """
    # Prefer direct connection IP (most secure)
    if request.client:
        return request.client.host

    # Fallback to X-Forwarded-For (can be spoofed, use with caution)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2)
        # Take the first one (client IP)
        return forwarded_for.split(",")[0].strip()

    # Ultimate fallback
    return "unknown"


@router.post(
    "/request-magic-link",
    response_model=RecoverPlanResponse,
    status_code=200,
    summary="Request magic link for plan recovery",
    description=(
        "Send magic link to email for passwordless plan recovery. "
        "Rate limited to 3 requests per email per 24h and 5 requests per IP per hour. "
        "Returns generic success message to prevent email enumeration."
    ),
)
async def request_magic_link(
    request_data: RecoverPlanRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RecoverPlanResponse:
    """
    Request magic link for plan recovery (T093).

    This endpoint generates a secure magic link token and sends it via email
    to the user. Implements comprehensive rate limiting and security measures
    to prevent abuse.

    Rate Limits:
    - Email-based: 3 requests per email per 24 hours
    - IP-based: 5 requests per IP per hour

    Security Features:
    - Generic response prevents email enumeration
    - Crypto-secure 256-bit tokens
    - Single-use enforcement
    - 24-hour expiration
    - IP logging for audit trail

    Args:
        request_data: Email address to send magic link to
        request: FastAPI request object (for IP extraction)
        db: Database session

    Returns:
        RecoverPlanResponse: Generic success message

    Raises:
        HTTPException 429: Rate limit exceeded
        HTTPException 500: Server error (email send failed, etc.)

    Example:
        POST /api/v1/recovery/request-magic-link
        {
            "email": "user@example.com"
        }

        Response:
        {
            "message": "If a meal plan exists for this email, you'll receive a magic link within 5 minutes."
        }

    Reference:
        specs/001-keto-meal-plan-generator/contracts/recovery-api.yaml
        Phase 7.1 - Magic link generation (T090-T093)
    """
    email = request_data.email
    client_ip = get_client_ip(request)

    logger.info(f"Magic link request from {email} (ip: {client_ip})")

    # T091: Check rate limits
    # Email-based: 3 per email per 24 hours
    try:
        await check_rate_limit_email(
            email=email,
            limit=3,
            window_seconds=86400,  # 24 hours
            operation="magic_link",
        )
    except RateLimitExceeded as e:
        logger.warning(
            f"Email rate limit exceeded for {email} "
            f"({e.current_count}/{e.limit} requests)"
        )
        raise HTTPException(
            status_code=429,
            detail={
                "code": "RATE_LIMITED",
                "message": str(e),
                "retry_after": e.reset_time.isoformat() if e.reset_time else None,
            }
        )

    # T091: IP-based: 5 per IP per hour
    try:
        await check_rate_limit_ip(
            ip_address=client_ip,
            limit=5,
            window_seconds=3600,  # 1 hour
            operation="magic_link",
        )
    except RateLimitExceeded as e:
        logger.warning(
            f"IP rate limit exceeded for {client_ip} "
            f"({e.current_count}/{e.limit} requests)"
        )
        raise HTTPException(
            status_code=429,
            detail={
                "code": "RATE_LIMITED",
                "message": str(e),
                "retry_after": e.reset_time.isoformat() if e.reset_time else None,
            }
        )

    # T090: Generate magic link token
    try:
        token, token_record = await generate_magic_link_token(
            email=email,
            ip_address=client_ip,
            db=db,
        )

        # Build magic link URL
        magic_link_url = f"{APP_URL}/verify-magic-link?token={token}"

        logger.info(
            f"Magic link token generated for {email} "
            f"(expires: {token_record.expires_at.isoformat()})"
        )

    except Exception as e:
        logger.error(
            f"Failed to generate magic link token for {email}: {type(e).__name__}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVER_ERROR",
                "message": "Failed to generate magic link. Please try again later."
            }
        )

    # T093: Send magic link via email
    try:
        email_result = await send_magic_link_email(
            to_email=email,
            magic_link_url=magic_link_url,
        )

        if not email_result["success"]:
            logger.error(
                f"Failed to send magic link email to {email}: {email_result.get('error')}"
            )
            # Don't expose email send failure to prevent enumeration
            # Still return generic success message

    except Exception as e:
        logger.error(
            f"Exception while sending magic link email to {email}: {type(e).__name__}: {e}",
            exc_info=True
        )
        # Don't expose error to prevent enumeration
        # Still return generic success message

    # T093: Return generic success message (prevent email enumeration)
    # Same response whether email exists or not, whether email sent or not
    return RecoverPlanResponse(
        message=(
            "If a meal plan exists for this email, you'll receive a magic link within 5 minutes. "
            "Check your spam folder if you don't see it."
        )
    )


@router.get(
    "/verify",
    response_model=MagicLinkVerifyResponse,
    status_code=200,
    summary="Verify magic link token",
    description=(
        "Verify magic link token and return meal plan details. "
        "Token must be valid, unused, and not expired (24h validity). "
        "Single-use enforcement: token is marked as used immediately upon verification."
    ),
    responses={
        200: {
            "description": "Token verified successfully",
            "model": MagicLinkVerifyResponse,
        },
        400: {
            "description": "Invalid, expired, or already used token",
            "model": MagicLinkVerifyErrorResponse,
        },
        404: {
            "description": "No meal plans found for this token",
            "model": MagicLinkVerifyErrorResponse,
        },
    },
)
async def verify_magic_link(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MagicLinkVerifyResponse:
    """
    Verify magic link token and return meal plan details (T094-T096).

    This endpoint validates the magic link token sent via email and returns
    the associated meal plan details if the token is valid. Implements
    comprehensive security measures including:

    Token Validation (T094):
    - Token must exist in database (SHA256 hash lookup)
    - Token must not be expired (24h from creation)
    - Token must not be used (used_at IS NULL)

    Single-Use Enforcement (T095):
    - On successful verification, token is marked as used immediately
    - Subsequent attempts return "Token already used" error
    - Atomic database transaction prevents race conditions

    IP Address Logging (T096):
    - generation_ip logged when token is created (Phase 7.1)
    - usage_ip logged when token is verified (this endpoint)
    - If IPs don't match, warning logged to Sentry (but request NOT blocked)
    - IP mismatch is normal if user switches networks (WiFi to mobile data)

    Args:
        token: Magic link token from email (query parameter)
        request: FastAPI request object (for IP extraction)
        db: Database session

    Returns:
        MagicLinkVerifyResponse: Meal plan details (id, email, created_at, pdf_available)

    Raises:
        HTTPException 400: Invalid, expired, or already used token
        HTTPException 404: No meal plans found for this token
        HTTPException 500: Server error (database error, etc.)

    Example:
        GET /api/v1/recovery/verify?token=abc123...

        Success Response (200):
        {
            "meal_plan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "email": "user@example.com",
            "created_at": "2024-01-15T14:30:00Z",
            "pdf_available": true
        }

        Error Response (400 - Token Expired):
        {
            "code": "TOKEN_EXPIRED",
            "message": "This magic link has expired. Please request a new one."
        }

        Error Response (400 - Token Already Used):
        {
            "code": "TOKEN_ALREADY_USED",
            "message": "This magic link has already been used. Please request a new one."
        }

        Error Response (400 - Token Invalid):
        {
            "code": "TOKEN_INVALID",
            "message": "Invalid magic link. Please request a new one."
        }

        Error Response (404 - No Meal Plans):
        {
            "code": "NO_MEAL_PLANS",
            "message": "No meal plans found for this account."
        }

    Reference:
        specs/001-keto-meal-plan-generator/contracts/recovery-api.yaml
        Phase 7.2 - Magic link verification (T094-T096)
    """
    client_ip = get_client_ip(request)

    logger.info(f"Magic link verification request (ip: {client_ip}, token: {token[:8]}...)")

    # T094: Verify token and get meal plan IDs
    token_record, meal_plan_ids = await verify_magic_link_token(
        token=token,
        ip_address=client_ip,
        db=db,
    )

    # Token validation failed
    if not token_record:
        # We need to determine the specific error
        # Re-query to check if token exists and get details
        import hashlib
        from sqlalchemy import select
        from src.models.magic_link import MagicLinkToken

        token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
        result = await db.execute(
            select(MagicLinkToken).where(MagicLinkToken.token_hash == token_hash)
        )
        existing_token = result.scalar_one_or_none()

        if not existing_token:
            # Token doesn't exist
            logger.warning(f"Invalid token verification attempt (ip: {client_ip})")
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "TOKEN_INVALID",
                    "message": "Invalid magic link. Please request a new one."
                }
            )

        # Check expiration BEFORE checking used_at
        # This ensures we return "expired" message even if token was marked as used during expiration check
        from datetime import datetime
        if datetime.utcnow() > existing_token.expires_at:
            logger.warning(
                f"Expired token verification attempt for {existing_token.normalized_email} "
                f"(ip: {client_ip})"
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "TOKEN_EXPIRED",
                    "message": "This magic link has expired. Please request a new one."
                }
            )

        # Now check if token was already used (and not expired)
        if existing_token.used_at:
            # Token already used (T095)
            logger.warning(
                f"Already-used token verification attempt for {existing_token.normalized_email} "
                f"(ip: {client_ip})"
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "TOKEN_ALREADY_USED",
                    "message": "This magic link has already been used. Please request a new one."
                }
            )

    # No meal plans found for this email
    if not meal_plan_ids:
        logger.warning(
            f"No meal plans found for {token_record.normalized_email} "
            f"(ip: {client_ip})"
        )
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NO_MEAL_PLANS",
                "message": "No meal plans found for this account."
            }
        )

    # Get meal plan details
    # For simplicity, return the first meal plan (most recent)
    # In future, we could return multiple meal plans
    from sqlalchemy import select, desc
    result = await db.execute(
        select(MealPlan)
        .where(MealPlan.id == meal_plan_ids[0])
    )
    meal_plan = result.scalar_one_or_none()

    if not meal_plan:
        logger.error(
            f"Meal plan {meal_plan_ids[0]} not found in database "
            f"(ip: {client_ip})"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVER_ERROR",
                "message": "Failed to retrieve meal plan details. Please try again later."
            }
        )

    # Check if PDF is available
    pdf_available = bool(meal_plan.pdf_blob_path and meal_plan.status == "completed")

    logger.info(
        f"Magic link verified successfully for {token_record.normalized_email} "
        f"(meal_plan_id: {meal_plan.id}, ip: {client_ip})"
    )

    return MagicLinkVerifyResponse(
        meal_plan_id=meal_plan.id,
        email=token_record.email,
        created_at=meal_plan.created_at,
        pdf_available=pdf_available,
    )
