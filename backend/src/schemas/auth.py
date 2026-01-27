"""
Pydantic schemas for email verification, payment checkout, and account registration.

Based on: specs/001-keto-meal-plan-generator/contracts/quiz-api.yaml
Functional requirements: FR-Q-019, FR-P-003, FR-P-007, FR-R-001

Account Registration (Phase 7.3):
- RegisterRequest: Account creation with optional signup token
- RegisterResponse: JWT access token after successful registration

Email Verification (Phase 6.1):
- EmailVerificationCodeRequest/Response: Send verification code
- EmailVerificationRequest/Response: Verify code

Checkout (Phase 6.2):
- CheckoutInitiateRequest/Response: Paddle checkout session
"""

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


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


# =============================================================================
# Account Registration Schemas (Phase 7.3)
# =============================================================================


class RegisterRequest(BaseModel):
    """
    Account registration request.

    Supports two registration flows:
    1. Direct registration: User provides email + password
    2. Token-based registration: User clicks link from delivery email,
       token pre-fills email (readonly), user provides password

    Attributes:
        email: User email address (validated, normalized)
        password: User password (min 8 chars, max 128 chars)
        signup_token: Optional JWT token from delivery email link

    Validation:
        - Email: RFC 5322 format (via EmailStr)
        - Password: 8-128 characters, no other complexity requirements
        - If signup_token provided, email from token must match email field

    Example:
        # Direct registration
        {
            "email": "user@example.com",
            "password": "SecurePassword123!",
            "signup_token": null
        }

        # Token-based registration (from email link)
        {
            "email": "user@example.com",  # Pre-filled from token, readonly
            "password": "SecurePassword123!",
            "signup_token": "eyJhbGc..."
        }

    Security Notes:
        - Password is validated for length only (no complexity requirements)
        - Password will be hashed with bcrypt before storage (never stored plain)
        - Email is normalized (lowercase, Gmail alias handling) before DB insert
        - Signup token is verified in endpoint (signature, expiration, email match)

    Reference:
        tasks.md T098 (Account registration endpoint)
        FR-R-001 (Email must match purchase email)
    """

    email: EmailStr = Field(
        ...,
        description="User email address (must be valid format)",
        examples=["user@example.com"]
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (minimum 8 characters)",
        examples=["SecurePassword123!"]
    )

    signup_token: Optional[str] = Field(
        None,
        description=(
            "Optional signup token from delivery email link. "
            "If provided, email must match token's encoded email."
        ),
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validate password requirements.

        Requirements:
        - Minimum 8 characters
        - Maximum 128 characters (enforced by Field)
        - No complexity requirements (letters/numbers/symbols optional)

        Note: Additional complexity requirements can be added here if needed.
        Current simple validation aligns with modern UX best practices
        (favor length over complexity).

        Args:
            v: Password string to validate

        Returns:
            str: Validated password

        Raises:
            ValueError: If password doesn't meet requirements
        """
        # Length validation is handled by Field(min_length, max_length)
        # Add additional complexity checks here if needed
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123!",
                "signup_token": None
            }
        }
    )


class RegisterResponse(BaseModel):
    """
    Successful account registration response.

    Returns JWT access token for immediate authentication after registration.

    Attributes:
        access_token: JWT token for API authentication (24h expiry)
        token_type: Token type (always "bearer")
        user_id: Created user ID (UUID string)
        email: User email address (normalized)

    Example:
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com"
        }

    Usage:
        # Client stores access_token and includes in subsequent requests:
        # Authorization: Bearer eyJhbGc...

    Reference:
        tasks.md T098 (Return JWT access token on successful registration)
    """

    access_token: str = Field(
        ...,
        description="JWT access token for API authentication (expires in 24 hours)"
    )

    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')"
    )

    user_id: str = Field(
        ...,
        description="Created user ID (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )

    email: str = Field(
        ...,
        description="User email address (normalized)",
        examples=["user@example.com"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com"
            }
        }
    )


# =============================================================================
# Login Schemas (Phase 7.3)
# =============================================================================


class LoginRequest(BaseModel):
    """
    Login request with email and password.

    Attributes:
        email: User email address (validated)
        password: User password (plain text, will be verified against hash)

    Example:
        {
            "email": "user@example.com",
            "password": "SecurePassword123!"
        }

    Security Notes:
        - Password is transmitted over HTTPS (never plain HTTP)
        - Password is verified against bcrypt hash in database
        - Never logged or returned in responses

    Reference:
        tasks.md T098 (Account registration endpoint)
        Phase 7.3 - Optional Account Creation
    """

    email: EmailStr = Field(
        ...,
        description="User email address (must be valid format)",
        examples=["user@example.com"]
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password",
        examples=["SecurePassword123!"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123!"
            }
        }
    )


class LoginResponse(BaseModel):
    """
    Successful login response.

    Returns JWT access token for API authentication.

    Attributes:
        access_token: JWT token for API authentication (24h expiry)
        token_type: Token type (always "bearer")
        user_id: User ID (UUID string)
        email: User email address (normalized)

    Example:
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com"
        }

    Usage:
        # Client stores access_token and includes in subsequent requests:
        # Authorization: Bearer eyJhbGc...

    Reference:
        tasks.md T098 (Account registration endpoint)
        Phase 7.3 - Optional Account Creation
    """

    access_token: str = Field(
        ...,
        description="JWT access token for API authentication (expires in 24 hours)"
    )

    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')"
    )

    user_id: str = Field(
        ...,
        description="User ID (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )

    email: str = Field(
        ...,
        description="User email address (normalized)",
        examples=["user@example.com"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com"
            }
        }
    )
