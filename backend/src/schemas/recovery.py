"""
Pydantic schemas for PDF recovery via magic links and account management.

Based on: specs/001-keto-meal-plan-generator/contracts/recovery-api.yaml
Functional requirements: FR-R-001 to FR-R-005, FR-E-007
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


class RecoverPlanRequest(BaseModel):
    """
    Request magic link for PDF recovery.

    Security:
    - Rate limit: 5 requests per IP per hour (prevents enumeration)
    - Magic link: 256-bit token, 24-hour expiry, single-use
    - Rate limit magic link requests: 3 per email per 24h

    Functional requirements: FR-E-007, FR-R-002
    """
    email: EmailStr = Field(
        description="Email address to send magic link to",
        examples=["user@example.com"]
    )


class RecoverPlanResponse(BaseModel):
    """
    Response after requesting magic link.

    Generic response prevents email enumeration attacks.
    Functional requirement: FR-R-002
    """
    message: str = Field(
        description="Generic success message (same response whether email exists or not)",
        examples=["If a meal plan exists for this email, you'll receive a magic link within 5 minutes."]
    )


class MagicLinkVerifyResponse(BaseModel):
    """
    Response after verifying magic link token.

    Grants 24-hour session for PDF access.
    Functional requirement: FR-R-002
    """
    access_granted: bool = Field(
        description="Whether magic link verification succeeded",
        examples=[True]
    )
    meal_plan_id: UUID = Field(
        description="Meal plan ID for PDF download",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
    )
    email: EmailStr = Field(
        description="Email address associated with meal plan",
        examples=["user@example.com"]
    )
    expires_at: datetime = Field(
        description="Magic link session expiry (24 hours from first use)",
        examples=["2024-01-15T14:30:00Z"]
    )


class AccountCreateRequest(BaseModel):
    """
    Request to create optional account.

    Account email MUST match purchase email.
    Available at 3 touchpoints:
    1. Mid-quiz (Step 10) - enables cross-device sync
    2. Post-purchase success page
    3. Email link after PDF delivery

    Functional requirement: FR-R-001
    """
    email: EmailStr = Field(
        description="Email address (must match purchase email if from touchpoint 2/3)",
        examples=["user@example.com"]
    )
    password: str = Field(
        min_length=8,
        description="Password (minimum 8 characters)",
        examples=["SecurePassword123!"]
    )
    signup_token: Optional[str] = Field(
        default=None,
        description="Signed token from email link (touchpoint 3) encoding purchase_email",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce minimum password requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        # Additional password strength checks can be added here
        # (uppercase, lowercase, numbers, special chars)
        return v


class AccountCreateResponse(BaseModel):
    """
    Response after successful account creation.

    Functional requirement: FR-R-001
    """
    user_id: UUID = Field(
        description="Unique user identifier",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
    )
    email: EmailStr = Field(
        description="Account email address",
        examples=["user@example.com"]
    )
    access_token: str = Field(
        description="JWT token for authenticated API calls",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )


class DashboardMealPlan(BaseModel):
    """
    Meal plan data for dashboard display.

    Functional requirement: FR-R-004
    """
    id: UUID = Field(
        description="Meal plan identifier",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
    )
    created_at: datetime = Field(
        description="Meal plan creation timestamp",
        examples=["2024-01-01T12:00:00Z"]
    )
    calorie_target: int = Field(
        ge=1000,
        le=4000,
        description="Daily calorie target",
        examples=[1650]
    )
    days_remaining: int = Field(
        ge=0,
        le=90,
        description="Days until 90-day expiration",
        examples=[67]
    )
    download_available: bool = Field(
        description="Whether PDF download is available (false if expired)",
        examples=[True]
    )


class DashboardResponse(BaseModel):
    """
    Dashboard data for authenticated user.

    Functional requirement: FR-R-004
    """
    email: EmailStr = Field(
        description="User's email address",
        examples=["user@example.com"]
    )
    meal_plan: Optional[DashboardMealPlan] = Field(
        default=None,
        description="User's meal plan (null if none exists)"
    )


class DownloadPDFResponse(BaseModel):
    """
    Response for PDF download endpoint (302 redirect).

    This schema documents the redirect behavior, though the actual
    response will be a 302 redirect with Location header.

    Functional requirement: FR-R-005
    """
    redirect_url: str = Field(
        description="Vercel Blob signed URL for PDF download (in Location header)",
        examples=["https://blob.vercel-storage.com/abc123.pdf?signature=xyz..."]
    )
