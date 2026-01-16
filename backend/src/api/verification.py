"""
Email verification API endpoints.

This module provides email verification endpoints for unauthenticated users during
checkout. Verified status persists for 24 hours, allowing users to abandon and
return to payment without re-verification (FR-Q-019).

Endpoints:
    POST /verification/send-code - Request verification code via email
    POST /verification/verify-code - Validate code and mark email verified
    GET /verification/status/{email} - Check verification status (utility)

Security:
    - Rate limiting via 60-second cooldown
    - 10-minute code expiry
    - 24-hour verified status validity
    - Email normalization (Gmail dot/plus removal)
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator, EmailStr

from src.services.email_verification import (
    send_verification_code,
    verify_code,
    is_email_verified,
    get_verification_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verification", tags=["verification"])


# Pydantic schemas for request/response validation
class SendCodeRequest(BaseModel):
    """Request model for sending verification code."""

    email: EmailStr = Field(
        ...,
        description="Email address to send verification code to",
        examples=["user@example.com"],
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Ensure email is lowercase and trimmed."""
        return v.strip().lower()


class SendCodeResponse(BaseModel):
    """Response model for send code endpoint."""

    success: bool = Field(..., description="Whether code was sent successfully")
    message: str = Field(..., description="User-friendly message")
    code: Optional[str] = Field(
        None,
        description="Verification code (only in development/testing)",
    )
    cooldown_remaining: Optional[int] = Field(
        None,
        description="Seconds until next send allowed (only if cooldown active)",
    )


class VerifyCodeRequest(BaseModel):
    """Request model for code verification."""

    email: EmailStr = Field(
        ...,
        description="Email address to verify",
        examples=["user@example.com"],
    )
    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit verification code",
        examples=["123456"],
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Ensure email is lowercase and trimmed."""
        return v.strip().lower()

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Ensure code is trimmed."""
        return v.strip()


class VerifyCodeResponse(BaseModel):
    """Response model for code verification endpoint."""

    success: bool = Field(..., description="Whether verification succeeded")
    message: str = Field(..., description="User-friendly message")
    verified_until: Optional[datetime] = Field(
        None,
        description="Timestamp when verification expires (24 hours from now)",
    )


class VerificationStatusResponse(BaseModel):
    """Response model for verification status endpoint."""

    email: str = Field(..., description="Email address checked")
    verified: bool = Field(..., description="Whether email is currently verified")
    verified_ttl: Optional[int] = Field(
        None,
        description="Seconds until verification expires (only if verified)",
    )


# API Endpoints
@router.post(
    "/send-code",
    response_model=SendCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Send verification code",
    description=(
        "Generate and send a 6-digit verification code to the provided email. "
        "Code expires in 10 minutes. Rate limited to 1 request per 60 seconds per email."
    ),
    responses={
        200: {
            "description": "Code sent successfully or email already verified",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Verification code sent (expires in 10 minutes)",
                        "code": "123456",
                    }
                }
            },
        },
        400: {
            "description": "Bad request - email already verified",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "email_already_verified",
                            "message": "Email already verified for the next 24 hours",
                        }
                    }
                }
            },
        },
        422: {
            "description": "Validation error - invalid email format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "email"],
                                "msg": "value is not a valid email address",
                                "type": "value_error.email",
                            }
                        ]
                    }
                }
            },
        },
        429: {
            "description": "Too many requests - cooldown active",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "rate_limit_exceeded",
                            "message": "Please wait 45 seconds before requesting a new code",
                            "cooldown_remaining": 45,
                        }
                    }
                }
            },
        },
    },
)
async def send_code(request: SendCodeRequest) -> SendCodeResponse:
    """
    Send verification code to email address.

    This endpoint:
    1. Validates email format (handled by Pydantic)
    2. Checks if email is already verified (24h status)
    3. Enforces 60-second cooldown between sends
    4. Generates cryptographically secure 6-digit code
    5. Stores code in Redis with 10-minute TTL

    Args:
        request: SendCodeRequest with email address

    Returns:
        SendCodeResponse with success status, message, and optional code/cooldown

    Raises:
        HTTPException 400: Email already verified
        HTTPException 422: Invalid email format
        HTTPException 429: Cooldown active
        HTTPException 500: Internal server error
    """
    try:
        logger.info(f"Send verification code request for email: {request.email}")

        # Call service layer
        result = await send_verification_code(request.email)

        if not result["success"]:
            error_msg = result.get("error", "Unknown error")
            cooldown_remaining = result.get("cooldown_remaining")

            # Cooldown active - rate limit
            if cooldown_remaining is not None:
                logger.warning(
                    f"Rate limit exceeded for {request.email}: {cooldown_remaining}s remaining"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "rate_limit_exceeded",
                        "message": error_msg,
                        "cooldown_remaining": cooldown_remaining,
                    },
                )

            # Email already verified
            if "already verified" in error_msg.lower():
                logger.info(f"Email already verified: {request.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "email_already_verified",
                        "message": error_msg,
                    },
                )

            # Other errors (invalid email, Redis failure, etc.)
            logger.error(f"Failed to send verification code: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "send_code_failed",
                    "message": error_msg,
                },
            )

        # Success - return response
        logger.info(f"Verification code sent successfully to {request.email}")
        return SendCodeResponse(
            success=True,
            message=result.get("message", "Verification code sent"),
            code=result.get("code"),  # Only present in dev/testing
            cooldown_remaining=None,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (already handled)
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in send_code endpoint: {type(e).__name__}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "internal_server_error",
                "message": "Failed to send verification code. Please try again.",
            },
        )


@router.post(
    "/verify-code",
    response_model=VerifyCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify email code",
    description=(
        "Validate 6-digit verification code and mark email as verified for 24 hours. "
        "Code is consumed after successful verification (one-time use)."
    ),
    responses={
        200: {
            "description": "Code verified successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Email verified successfully. Valid for 24 hours.",
                        "verified_until": "2026-01-17T14:30:00Z",
                    }
                }
            },
        },
        400: {
            "description": "Invalid or expired code",
            "content": {
                "application/json": {
                    "examples": {
                        "expired": {
                            "summary": "Code expired",
                            "value": {
                                "detail": {
                                    "code": "code_expired",
                                    "message": "Verification code expired or not found. Please request a new code.",
                                }
                            },
                        },
                        "invalid": {
                            "summary": "Invalid code",
                            "value": {
                                "detail": {
                                    "code": "code_invalid",
                                    "message": "Invalid verification code. Please check and try again.",
                                }
                            },
                        },
                    }
                }
            },
        },
        422: {
            "description": "Validation error - code must be 6 digits",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "code"],
                                "msg": "ensure this value has at least 6 characters",
                                "type": "value_error.any_str.min_length",
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def verify_email_code(request: VerifyCodeRequest) -> VerifyCodeResponse:
    """
    Verify email with 6-digit code and mark as verified for 24 hours.

    This endpoint:
    1. Validates email and code format (handled by Pydantic)
    2. Retrieves stored code from Redis
    3. Uses constant-time comparison (prevent timing attacks)
    4. Marks email as verified for 24 hours on success
    5. Deletes used code (one-time use)

    Args:
        request: VerifyCodeRequest with email and code

    Returns:
        VerifyCodeResponse with success status and verification expiry

    Raises:
        HTTPException 400: Invalid or expired code
        HTTPException 422: Validation error (format)
        HTTPException 500: Internal server error
    """
    try:
        logger.info(f"Verify code request for email: {request.email}")

        # Call service layer
        result = await verify_code(request.email, request.code)

        if not result["success"]:
            error_msg = result.get("error", "Unknown error")

            # Code expired or not found
            if "expired" in error_msg.lower() or "not found" in error_msg.lower():
                logger.warning(f"Code expired/not found for {request.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "code_expired",
                        "message": error_msg,
                    },
                )

            # Invalid code (mismatch)
            if "invalid" in error_msg.lower():
                logger.warning(f"Invalid code for {request.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "code_invalid",
                        "message": error_msg,
                    },
                )

            # Other errors (Redis failure, etc.)
            logger.error(f"Verification failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "verification_failed",
                    "message": error_msg,
                },
            )

        # Success - calculate verified_until timestamp
        verified_until = datetime.utcnow()
        # Add 24 hours (could import from service constants but hardcoded for clarity)
        from datetime import timedelta
        verified_until = verified_until + timedelta(hours=24)

        logger.info(f"Email verified successfully: {request.email}")
        return VerifyCodeResponse(
            success=True,
            message=result.get("message", "Email verified successfully"),
            verified_until=verified_until,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (already handled)
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in verify_code endpoint: {type(e).__name__}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "internal_server_error",
                "message": "Verification failed. Please try again.",
            },
        )


@router.get(
    "/status/{email}",
    response_model=VerificationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check verification status",
    description=(
        "Check if an email address is currently verified (within 24-hour window). "
        "Utility endpoint for debugging and frontend state management."
    ),
    responses={
        200: {
            "description": "Verification status retrieved",
            "content": {
                "application/json": {
                    "examples": {
                        "verified": {
                            "summary": "Email verified",
                            "value": {
                                "email": "user@example.com",
                                "verified": True,
                                "verified_ttl": 86399,
                            },
                        },
                        "not_verified": {
                            "summary": "Email not verified",
                            "value": {
                                "email": "user@example.com",
                                "verified": False,
                                "verified_ttl": None,
                            },
                        },
                    }
                }
            },
        },
        422: {
            "description": "Invalid email format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["path", "email"],
                                "msg": "value is not a valid email address",
                                "type": "value_error.email",
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def check_verification_status(email: EmailStr) -> VerificationStatusResponse:
    """
    Check if email is currently verified (within 24-hour window).

    This endpoint:
    1. Validates email format (handled by FastAPI)
    2. Checks Redis for active verified status
    3. Returns verification state and TTL

    Args:
        email: Email address to check (path parameter)

    Returns:
        VerificationStatusResponse with verification status and TTL

    Raises:
        HTTPException 422: Invalid email format
        HTTPException 500: Internal server error
    """
    try:
        # Normalize email (lowercase, trim)
        normalized_email = email.strip().lower()
        logger.info(f"Check verification status for email: {normalized_email}")

        # Check if email is verified
        verified = await is_email_verified(normalized_email)

        # Get detailed status for TTL
        status_result = await get_verification_status(normalized_email)
        verified_ttl = status_result.get("verified_ttl") if status_result else None
        verified_ttl = verified_ttl if verified_ttl and verified_ttl > 0 else None

        logger.info(
            f"Verification status for {normalized_email}: verified={verified}, ttl={verified_ttl}"
        )

        return VerificationStatusResponse(
            email=normalized_email,
            verified=verified,
            verified_ttl=verified_ttl,
        )

    except Exception as e:
        logger.error(
            f"Unexpected error in check_verification_status endpoint: {type(e).__name__}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "internal_server_error",
                "message": "Failed to check verification status. Please try again.",
            },
        )
