"""
Pydantic schemas for email verification and payment checkout.

Based on: specs/001-keto-meal-plan-generator/contracts/quiz-api.yaml
Functional requirements: FR-Q-019, FR-P-003, FR-P-007
"""

from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


class EmailVerificationCodeRequest(BaseModel):
    """
    Request to send 6-digit email verification code.

    Rate limited: 60-second cooldown between requests per email.
    Functional requirement: FR-Q-019
    """
    email: EmailStr = Field(
        description="Email address to send verification code to",
        examples=["user@example.com"]
    )


class EmailVerificationCodeResponse(BaseModel):
    """
    Response after sending verification code email.

    Functional requirement: FR-Q-019
    """
    message: str = Field(
        description="Confirmation message",
        examples=["Verification code sent to user@example.com"]
    )
    expires_in_seconds: int = Field(
        description="Time until code expires (10 minutes = 600 seconds)",
        examples=[600]
    )


class EmailVerificationRequest(BaseModel):
    """
    Request to verify 6-digit email code.

    Code expires after 10 minutes.
    Functional requirement: FR-Q-019
    """
    email: EmailStr = Field(
        description="Email address being verified",
        examples=["user@example.com"]
    )
    code: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit verification code sent to email",
        examples=["123456"]
    )

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        """Ensure code is exactly 6 digits."""
        if not v.isdigit():
            raise ValueError("Code must contain only digits")
        if len(v) != 6:
            raise ValueError("Code must be exactly 6 digits")
        return v


class EmailVerificationResponse(BaseModel):
    """
    Response after successful email verification.

    Enables "Proceed to Payment" button.
    Functional requirement: FR-Q-019
    """
    verified: bool = Field(
        description="Whether email was successfully verified",
        examples=[True]
    )
    verification_token: str = Field(
        description="JWT token to pass to Paddle checkout for payment authorization",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )


class CheckoutInitiateRequest(BaseModel):
    """
    Request to initiate Paddle checkout session.

    Acquires distributed lock to prevent concurrent payments for same email.
    Functional requirements: FR-P-003, FR-P-007
    """
    quiz_id: UUID = Field(
        description="Quiz ID from /quiz/submit response",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
    )
    verification_token: str = Field(
        description="JWT token from /email/verify-code response",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )


class CheckoutInitiateResponse(BaseModel):
    """
    Response with Paddle checkout session URL.

    Functional requirement: FR-P-003
    """
    checkout_url: str = Field(
        description="Paddle checkout modal URL for client-side redirect",
        examples=["https://checkout.paddle.com/session/abc123"]
    )
