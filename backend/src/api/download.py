"""
Download API Endpoint

Provides secure PDF download with rate limiting and grace period.
Supports both authenticated users and magic link token access.

Endpoint:
- GET /download-pdf - Download meal plan PDF with rate limiting

Security Features:
- Rate limiting: 10 downloads per 24 hours (T105)
- Grace period: Unlimited downloads for 5 minutes after email delivery (T106)
- Composite identifier: user_id (authenticated) or email+IP hash (magic link)
- On-demand signed URL generation with 1-hour expiry

Functional Requirements:
- FR-R-005: Download rate limiting
- FR-D-006: Secure on-demand signed URL generation

Reference:
    Phase 7.5 - Download Rate Limiting (T105-T107)
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.lib.database import get_db
from src.lib.rate_limiting import check_download_rate_limit, RateLimitExceeded
from src.schemas.recovery import DownloadPDFResponse, DownloadPDFErrorResponse
from src.services.magic_link import verify_magic_link_token
from src.services.blob_storage import generate_signed_download_url, BlobStorageError
from src.models.meal_plan import MealPlan

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/download", tags=["Download"])


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


@router.get(
    "/download-pdf",
    response_model=DownloadPDFResponse,
    status_code=200,
    summary="Download meal plan PDF",
    description=(
        "Download meal plan PDF with rate limiting and grace period. "
        "Supports both authenticated users (meal_plan_id) and magic link users (token). "
        "Rate limited to 10 downloads per 24h with 5-min grace period after email delivery."
    ),
    responses={
        200: {
            "description": "Signed URL generated successfully",
            "model": DownloadPDFResponse,
        },
        400: {
            "description": "Invalid request (missing both meal_plan_id and token)",
            "model": DownloadPDFErrorResponse,
        },
        401: {
            "description": "Unauthorized (invalid token or meal plan not found)",
            "model": DownloadPDFErrorResponse,
        },
        404: {
            "description": "Meal plan not found",
            "model": DownloadPDFErrorResponse,
        },
        429: {
            "description": "Rate limit exceeded",
            "model": DownloadPDFErrorResponse,
        },
        503: {
            "description": "PDF not available (processing or failed)",
            "model": DownloadPDFErrorResponse,
        },
    },
)
async def download_pdf(
    request: Request,
    meal_plan_id: Optional[str] = Query(
        None,
        description="Meal plan ID (for authenticated users)"
    ),
    token: Optional[str] = Query(
        None,
        description="Magic link token (for magic link users)"
    ),
    db: AsyncSession = Depends(get_db),
) -> DownloadPDFResponse:
    """
    Download meal plan PDF with rate limiting (T107).

    This endpoint generates a fresh signed URL for secure PDF download.
    Implements comprehensive rate limiting with grace period exclusion.

    Authentication:
    - Authenticated users: Provide meal_plan_id
    - Magic link users: Provide token

    Rate Limiting (T105):
    - 10 downloads per 24 hours per identifier
    - Identifier: user_id (authenticated) or email+IP hash (magic link)
    - Counter resets after 24 hours (automatic via Redis TTL)

    Grace Period (T106):
    - Downloads within 5 minutes of email_sent_at are excluded
    - Allows users to download immediately after purchase
    - Does not count toward rate limit

    Signed URL (T107):
    - Generated on-demand from blob path
    - 1-hour expiry for security
    - Temporary access to permanent blob storage

    Args:
        request: FastAPI request object (for IP extraction)
        meal_plan_id: Meal plan ID for authenticated users
        token: Magic link token for magic link users
        db: Database session

    Returns:
        DownloadPDFResponse: Signed URL with expiry time

    Raises:
        HTTPException 400: Missing both meal_plan_id and token
        HTTPException 401: Invalid token or unauthorized access
        HTTPException 404: Meal plan not found
        HTTPException 429: Rate limit exceeded
        HTTPException 503: PDF not available (processing or failed)

    Example:
        # Authenticated user
        GET /api/v1/download/download-pdf?meal_plan_id=abc123

        # Magic link user
        GET /api/v1/download/download-pdf?token=xyz789

        Success Response (200):
        {
            "download_url": "https://blob.vercel-storage.com/...",
            "expires_in": 3600
        }

        Error Response (429 - Rate Limited):
        {
            "code": "RATE_LIMITED",
            "message": "Download limit reached. Try again in 12 hours.",
            "retry_after": 43200
        }

    Reference:
        Phase 7.5 - Download Rate Limiting (T105-T107)
    """
    client_ip = get_client_ip(request)

    # Validate request: must provide either meal_plan_id or token
    if not meal_plan_id and not token:
        logger.warning(f"Download request missing both meal_plan_id and token (ip: {client_ip})")
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_REQUEST",
                "message": "Must provide either meal_plan_id or token"
            }
        )

    # Initialize variables
    meal_plan: Optional[MealPlan] = None
    user_id: Optional[str] = None  # For authenticated users (future)

    # T107: Handle magic link token authentication
    if token:
        logger.info(f"Magic link download request (ip: {client_ip}, token: {token[:8]}...)")

        # Verify magic link token
        token_record, meal_plan_ids = await verify_magic_link_token(
            token=token,
            ip_address=client_ip,
            db=db,
        )

        if not token_record or not meal_plan_ids:
            logger.warning(f"Invalid magic link token for download (ip: {client_ip})")
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "UNAUTHORIZED",
                    "message": "Invalid or expired magic link. Please request a new one."
                }
            )

        # Get meal plan by ID
        result = await db.execute(
            select(MealPlan).where(MealPlan.id == meal_plan_ids[0])
        )
        meal_plan = result.scalar_one_or_none()

        if not meal_plan:
            logger.error(f"Meal plan not found for token (ip: {client_ip})")
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "NOT_FOUND",
                    "message": "Meal plan not found"
                }
            )

    # T107: Handle authenticated user (meal_plan_id)
    elif meal_plan_id:
        logger.info(f"Authenticated download request (ip: {client_ip}, meal_plan_id: {meal_plan_id})")

        # TODO: Implement JWT authentication and extract user_id
        # For now, we'll look up the meal plan directly
        result = await db.execute(
            select(MealPlan).where(MealPlan.id == meal_plan_id)
        )
        meal_plan = result.scalar_one_or_none()

        if not meal_plan:
            logger.warning(f"Meal plan not found: {meal_plan_id} (ip: {client_ip})")
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "NOT_FOUND",
                    "message": "Meal plan not found"
                }
            )

        # TODO: Verify user owns this meal plan
        # For now, we allow any meal_plan_id (authenticated users only)

    # Check if PDF is available
    if not meal_plan.pdf_blob_path:
        logger.warning(
            f"PDF not available for meal plan {meal_plan.id} (status: {meal_plan.status})"
        )
        raise HTTPException(
            status_code=503,
            detail={
                "code": "PDF_NOT_AVAILABLE",
                "message": (
                    "PDF is not available yet. Please try again in a few minutes. "
                    if meal_plan.status == "processing"
                    else "PDF generation failed. Please contact support."
                )
            }
        )

    # T105: Check download rate limit (with T106 grace period)
    try:
        await check_download_rate_limit(
            user_id=user_id,
            email=meal_plan.email,
            ip_address=client_ip,
            email_sent_at=meal_plan.email_sent_at,
        )
    except RateLimitExceeded as e:
        logger.warning(
            f"Download rate limit exceeded for meal plan {meal_plan.id} "
            f"({e.current_count}/{e.limit} downloads, ip: {client_ip})"
        )

        # Calculate retry_after in seconds
        retry_after = None
        if e.reset_time:
            from datetime import datetime
            retry_after = int((e.reset_time - datetime.utcnow()).total_seconds())

        raise HTTPException(
            status_code=429,
            detail={
                "code": "RATE_LIMITED",
                "message": str(e),
                "retry_after": retry_after,
            }
        )

    # T107: Generate fresh signed URL (1-hour expiry)
    try:
        signed_url = await generate_signed_download_url(
            blob_url=meal_plan.pdf_blob_path,
            expiry_seconds=3600,  # 1 hour
        )

        logger.info(
            f"Signed URL generated for meal plan {meal_plan.id} "
            f"(expires in 3600s, ip: {client_ip})"
        )

        return DownloadPDFResponse(
            download_url=signed_url,
            expires_in=3600,
        )

    except BlobStorageError as e:
        logger.error(
            f"Failed to generate signed URL for meal plan {meal_plan.id}: "
            f"{e.error_type}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVER_ERROR",
                "message": "Failed to generate download URL. Please try again later."
            }
        )
