"""
Authentication API Endpoints

Provides account registration and authentication endpoints for optional user accounts.

Endpoints:
- POST /auth/register - Account registration with email + password

Features:
- Account creation with bcrypt password hashing
- Optional signup token validation (from delivery email)
- Email normalization to prevent duplicates
- JWT access token generation (24h expiry)
- Rate limiting: 5 registrations per IP per hour
- Duplicate email detection with user-friendly error

Security:
- Passwords hashed with bcrypt (12 rounds, auto-salting)
- Signup tokens validated with JWT signature + expiration
- Email from signup token must match registration email (FR-R-001)
- Rate limiting prevents abuse
- Never logs passwords or tokens

Reference:
    tasks.md T098 (Account registration endpoint)
    FR-R-001 (Email must match purchase email)
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.lib.database import get_db
from src.lib.email_utils import normalize_email
from src.lib.rate_limiting import check_rate_limit_ip, RateLimitExceeded
from src.models.user import User
from src.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
)
from src.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    verify_signup_token,
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth")


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.

    Checks X-Forwarded-For header for proxied requests, falls back to
    request.client.host for direct connections.

    Args:
        request: FastAPI Request object

    Returns:
        str: Client IP address (IPv4 or IPv6)

    Security Notes:
        - X-Forwarded-For can be spoofed (use with trusted proxy only)
        - For production, configure proxy to set X-Real-IP header
        - Falls back to direct connection IP if header not present
    """
    # Check for X-Forwarded-For header (set by reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2, ...)
        # First IP is the original client
        return forwarded_for.split(",")[0].strip()

    # Fallback to direct connection IP
    if request.client:
        return request.client.host

    # Default fallback (should never happen)
    return "unknown"


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    request_data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """
    Create new user account with email and password.

    Supports two registration flows:
    1. Direct registration: User provides email + password
    2. Token-based registration: User clicks link from delivery email,
       signup_token pre-fills email (readonly), user provides password

    Request Body:
        - email: User email address (validated, normalized)
        - password: User password (min 8 chars, hashed with bcrypt)
        - signup_token: Optional JWT token from delivery email link

    Response (201 Created):
        - access_token: JWT token for API authentication (24h expiry)
        - token_type: "bearer"
        - user_id: Created user UUID
        - email: Normalized email address

    Error Responses:
        - 400 Bad Request:
            - Email already registered (duplicate email)
            - Signup token invalid/expired
            - Email doesn't match signup token (FR-R-001)
        - 429 Too Many Requests:
            - Rate limit exceeded (5 per IP per hour)
        - 500 Internal Server Error:
            - Database error (rolled back, no partial state)

    Rate Limiting:
        - 5 registrations per IP per hour
        - Prevents abuse and spam account creation

    Email Normalization:
        - Lowercase all characters
        - Gmail: Remove dots and plus-suffixes
        - Prevents duplicate accounts via email aliases

    Password Security:
        - Hashed with bcrypt (12 rounds, auto-salting)
        - Never stored in plain text
        - Never logged or returned in responses

    Signup Token Validation (if provided):
        - Verify JWT signature (prevents tampering)
        - Check expiration (7-day expiry from delivery email)
        - Enforce email match: token.email == request.email (FR-R-001)

    Example:
        # Direct registration (no signup token)
        POST /auth/register
        {
            "email": "user@example.com",
            "password": "SecurePassword123!",
            "signup_token": null
        }

        Response (201):
        {
            "access_token": "eyJhbGc...",
            "token_type": "bearer",
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com"
        }

        # Token-based registration (from delivery email)
        POST /auth/register
        {
            "email": "user@example.com",  # Pre-filled from token, readonly
            "password": "SecurePassword123!",
            "signup_token": "eyJhbGc..."
        }

    Security Notes:
        - Rate limited to prevent brute-force and spam
        - Password hashed with bcrypt (never stored plain)
        - Email normalized to prevent duplicate accounts
        - Signup token validated (signature, expiration, email match)
        - Never logs passwords or tokens

    Reference:
        tasks.md T098 (Account registration endpoint)
        FR-R-001 (Email must match purchase email for signup token)
    """
    # Extract client IP for rate limiting
    client_ip = get_client_ip(request)

    # Rate limiting: 5 registrations per IP per hour
    try:
        await check_rate_limit_ip(
            ip_address=client_ip,
            limit=5,
            window_seconds=3600,  # 1 hour
            operation="register",
        )
    except RateLimitExceeded as e:
        logger.warning(
            f"Registration rate limit exceeded for IP {client_ip}: {e}"
        )
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many registration attempts. "
                "Please try again later."
            ),
        )

    # Normalize email for consistent storage and lookup
    normalized_email = normalize_email(request_data.email)

    # If signup token provided, validate it
    signup_token_payload: Optional[dict] = None
    if request_data.signup_token:
        signup_token_payload = verify_signup_token(request_data.signup_token)

        if not signup_token_payload:
            logger.warning(
                f"Invalid or expired signup token for email {normalized_email}"
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid or expired signup link. "
                    "Please request a new account creation link from your delivery email."
                ),
            )

        # FR-R-001: Email must match signup token email
        token_email = signup_token_payload.get("email")
        if token_email != normalized_email:
            logger.warning(
                f"Email mismatch: token email {token_email} != "
                f"request email {normalized_email}"
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    "Email address must match the one from your purchase. "
                    "You cannot change the email when creating an account from a signup link."
                ),
            )

        logger.info(
            f"Signup token validated for {normalized_email} "
            f"(meal_plan_id: {signup_token_payload.get('meal_plan_id')})"
        )

    # Hash password using bcrypt
    password_hash = hash_password(request_data.password)

    # Create user in database
    try:
        # Check if user already exists (explicit check for better error message)
        existing_user_stmt = select(User).where(
            User.normalized_email == normalized_email
        )
        result = await db.execute(existing_user_stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.warning(
                f"Registration attempt for existing email: {normalized_email}"
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    "An account with this email already exists. "
                    "Please log in instead."
                ),
            )

        # Create new user
        new_user = User(
            email=request_data.email,  # Store original email (for display)
            normalized_email=normalized_email,  # Store normalized email (for lookups)
            password_hash=password_hash,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        logger.info(
            f"User account created successfully: {normalized_email} "
            f"(user_id: {new_user.id}, "
            f"signup_token: {bool(request_data.signup_token)})"
        )

    except HTTPException:
        # Re-raise HTTPExceptions (e.g. duplicate email check above)
        raise
    except IntegrityError as e:
        # Database constraint violation (e.g., duplicate email race condition)
        await db.rollback()
        logger.error(
            f"Database integrity error during registration for {normalized_email}: {e}"
        )
        raise HTTPException(
            status_code=400,
            detail=(
                "An account with this email already exists. "
                "Please log in instead."
            ),
        )
    except Exception as e:
        # Unexpected database error
        await db.rollback()
        logger.error(
            f"Unexpected error during registration for {normalized_email}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to create account. Please try again later.",
        )

    # Generate JWT access token for immediate authentication
    access_token = create_access_token(
        user_id=new_user.id,
        email=new_user.email,
    )

    # Return success response with access token
    return RegisterResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=new_user.id,
        email=new_user.email,
    )


@router.post("/login", response_model=LoginResponse, status_code=200)
async def login(
    request_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Authenticate user with email and password.

    Verifies user credentials and returns JWT access token for API authentication.

    Request Body:
        - email: User email address (validated, normalized)
        - password: User password (verified against bcrypt hash)

    Response (200 OK):
        - access_token: JWT token for API authentication (24h expiry)
        - token_type: "bearer"
        - user_id: User UUID
        - email: User email address

    Error Responses:
        - 401 Unauthorized:
            - Invalid credentials (email doesn't exist or password incorrect)
        - 429 Too Many Requests:
            - Rate limit exceeded (5 per IP per 15 minutes)
        - 500 Internal Server Error:
            - Database error (logged for debugging)

    Rate Limiting:
        - 5 login attempts per IP per 15 minutes
        - Prevents brute-force attacks

    Email Normalization:
        - Email is normalized before lookup (lowercase, Gmail alias handling)
        - Ensures consistent user identification

    Password Verification:
        - Uses constant-time comparison (prevents timing attacks)
        - Verifies against bcrypt hash in database
        - Never logs password or hash values

    Example:
        # Login request
        POST /auth/login
        {
            "email": "user@example.com",
            "password": "SecurePassword123!"
        }

        Response (200):
        {
            "access_token": "eyJhbGc...",
            "token_type": "bearer",
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com"
        }

    Security Notes:
        - Rate limited to prevent brute-force attacks
        - Password verified with constant-time comparison
        - Email normalized to prevent duplicate accounts
        - Never logs passwords or tokens
        - Returns generic error message on invalid credentials (no user enumeration)

    Reference:
        tasks.md T098 (Account registration endpoint)
        Phase 7.3 - Optional Account Creation
    """
    # Extract client IP for rate limiting
    client_ip = get_client_ip(request)

    # Rate limiting: 5 login attempts per IP per 15 minutes (prevents brute-force)
    try:
        await check_rate_limit_ip(
            ip_address=client_ip,
            limit=5,
            window_seconds=900,  # 15 minutes
            operation="login",
        )
    except RateLimitExceeded as e:
        logger.warning(
            f"Login rate limit exceeded for IP {client_ip}: {e}"
        )
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many login attempts. "
                "Please try again later."
            ),
        )

    # Normalize email for consistent lookup
    normalized_email = normalize_email(request_data.email)

    # Query user by normalized email
    try:
        user_stmt = select(User).where(User.normalized_email == normalized_email)
        result = await db.execute(user_stmt)
        user = result.scalar_one_or_none()

        # User not found or password incorrect (generic error message)
        if not user:
            logger.warning(
                f"Login attempt for non-existent user: {normalized_email} "
                f"(IP: {client_ip})"
            )
            raise HTTPException(
                status_code=401,
                detail=(
                    "Invalid email or password. "
                    "Please check your credentials and try again."
                ),
            )

        # Verify password (constant-time comparison)
        if not user.password_hash or not verify_password(
            request_data.password, user.password_hash
        ):
            logger.warning(
                f"Invalid password for user: {normalized_email} "
                f"(IP: {client_ip})"
            )
            raise HTTPException(
                status_code=401,
                detail=(
                    "Invalid email or password. "
                    "Please check your credentials and try again."
                ),
            )

        logger.info(
            f"User logged in successfully: {normalized_email} "
            f"(user_id: {user.id}, IP: {client_ip})"
        )

    except HTTPException:
        # Re-raise HTTP exceptions (rate limit, invalid credentials)
        raise
    except Exception as e:
        # Unexpected database error
        logger.error(
            f"Unexpected error during login for {normalized_email}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Login failed. Please try again later.",
        )

    # Generate JWT access token
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
    )

    # Return success response with access token
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
    )
