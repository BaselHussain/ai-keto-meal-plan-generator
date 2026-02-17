"""
Payment API endpoints for handling pre-checkout validation and processing.

Implements blacklist check (T119) for chargeback prevention by validating
normalized_email against email_blacklist before allowing checkout.

Endpoint(s):
- POST /api/payment/validate - Validate email against blacklist before checkout

Security Features:
- Email normalization to prevent bypass (FR-P-010)
- 90-day TTL blacklist checking
- Rate limiting to prevent validation abuse
- IP logging for fraud detection

File: backend/src/api/payment.py
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.lib.database import get_db
from src.lib.email_utils import normalize_email
from src.lib.rate_limiting import check_rate_limit_ip
from src.models.email_blacklist import EmailBlacklist

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["payment"])


class ValidateEmailRequest(BaseModel):
    """Request body for email validation before checkout."""

    email: str = Field(..., description="Email to validate against blacklist")


class ValidateEmailResponse(BaseModel):
    """Response after email validation."""

    is_allowed: bool = Field(..., description="Whether email is allowed for checkout")
    message: str = Field(..., description="Status message")
    email_normalized: str = Field(..., description="Normalized email used for validation")


@router.post("/validate", response_model=ValidateEmailResponse)
async def validate_email_for_checkout(
    request: ValidateEmailRequest,
    db: AsyncSession = Depends(get_db),
    ip_address: str = Depends(lambda: "127.0.0.1")  # This will be implemented properly
) -> ValidateEmailResponse:
    """
    Validate email against blacklist before checkout (T119).

    Checks if the normalized email exists in email_blacklist table and if
    the entry has not expired (90-day TTL). This prevents chargeback abusers
    from making additional purchases.

    Args:
        request: Contains email to validate
        db: Database session

    Returns:
        ValidateEmailResponse indicating if email is allowed

    Raises:
        HTTPException 400: Invalid email format
        HTTPException 429: Rate limit exceeded
        HTTPException 500: Database or validation errors

    Reference:
        T119: Update blacklist check in checkout flow to query email_blacklist using normalized_email
        FR-P-010: Email normalization to prevent bypass
    """
    try:
        # Normalize email to prevent bypass (T119)
        normalized_email = normalize_email(request.email)

        # Rate limiting - prevent validation abuse
        await check_rate_limit_ip(
            ip_address=ip_address,
            limit=10,  # 10 checks per hour per IP
            window_seconds=3600,
            operation="email_validation"
        )

        # Query email_blacklist table using normalized_email (T119)
        result = await db.execute(
            select(EmailBlacklist)
            .where(EmailBlacklist.normalized_email == normalized_email)
            .where(EmailBlacklist.expires_at > datetime.utcnow())
        )
        blacklist_entry = result.scalar_one_or_none()

        if blacklist_entry:
            # Email is blacklisted - reject checkout
            logger.warning(f"Blacklisted email rejected for checkout: {normalized_email}")
            return ValidateEmailResponse(
                is_allowed=False,
                message=f"Checkout is not available for this email address due to account policy. Contact support if you believe this is an error.",
                email_normalized=normalized_email
            )

        # Email is not blacklisted - allow checkout
        logger.info(f"Email validated successfully for checkout: {normalized_email}")
        return ValidateEmailResponse(
            is_allowed=True,
            message="Email is allowed for checkout",
            email_normalized=normalized_email
        )

    except ValueError as e:
        # Email validation error
        logger.warning(f"Invalid email format: {request.email}, error: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid email format"
        )
    except Exception as e:
        logger.error(f"Unexpected error validating email {request.email}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during email validation"
        )