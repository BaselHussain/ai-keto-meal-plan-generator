"""
Authentication Service

Provides authentication utilities including password hashing, JWT token generation,
and signup token validation for optional account creation.

Features:
- Password hashing using bcrypt (via passlib)
- JWT access token generation with configurable expiry
- Signup token generation and validation (JWT-based, 7-day expiry)
- Constant-time token comparison for security
- User registration with email normalization

Security Standards:
- Password hashing: bcrypt with auto-salting (12 rounds default)
- JWT signing: HS256 algorithm with secret key
- Token expiry: Access token (24h), Signup token (7 days)
- Email normalization: Prevents duplicate accounts via Gmail aliases

Dependencies:
- passlib[bcrypt]: Password hashing
- python-jose[cryptography]: JWT token generation
- Environment variables: JWT_SECRET_KEY (required)

Usage:
    from src.services.auth_service import (
        hash_password,
        verify_password,
        create_access_token,
        create_signup_token,
        verify_signup_token,
    )

    # Hash password
    hashed = hash_password("user_password123")

    # Verify password
    is_valid = verify_password("user_password123", hashed)

    # Create access token
    token = create_access_token(user_id="user_123", email="user@example.com")

    # Create signup token (for email link)
    signup_token = create_signup_token(
        email="user@example.com",
        meal_plan_id="plan_123"
    )

    # Verify signup token
    payload = verify_signup_token(signup_token)
    # Returns: {"email": "user@example.com", "meal_plan_id": "plan_123"}
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import bcrypt
from jose import JWTError, jwt

from src.lib.email_utils import normalize_email

# Configure logging
logger = logging.getLogger(__name__)

# JWT configuration
# Load from environment (required for production)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    logger.warning(
        "JWT_SECRET_KEY not set in environment. "
        "Using default for development ONLY. "
        "Set JWT_SECRET_KEY in production!"
    )
    JWT_SECRET_KEY = "dev-secret-key-change-in-production-or-tokens-will-be-insecure"

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24  # Access token expires in 24 hours
SIGNUP_TOKEN_EXPIRE_DAYS = 7    # Signup token expires in 7 days


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Uses passlib's CryptContext with bcrypt scheme (12 rounds, auto-salting).
    The resulting hash includes the salt and can be verified with verify_password().

    Args:
        password: Plain text password to hash (min 8 characters recommended)

    Returns:
        str: Bcrypt hash in format $2b$12$[salt][hash] (60 chars)

    Example:
        >>> hashed = hash_password("SecurePassword123!")
        >>> print(hashed)
        '$2b$12$...'  # 60 character bcrypt hash

    Security Notes:
        - Never log the input password
        - Bcrypt includes automatic salting (no need to generate salt separately)
        - Hash is safe to store in database
        - 12 rounds is secure for 2026 (adjustable via CryptContext)

    Reference:
        research.md lines 1306-1450 (Password hashing best practices)
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its bcrypt hash.

    Uses bcrypt's constant-time comparison to prevent timing attacks.

    Args:
        plain_password: User-provided password to verify
        hashed_password: Stored bcrypt hash from database

    Returns:
        bool: True if password matches hash, False otherwise

    Example:
        >>> hashed = hash_password("SecurePassword123!")
        >>> verify_password("SecurePassword123!", hashed)
        True
        >>> verify_password("WrongPassword", hashed)
        False

    Security Notes:
        - Uses constant-time comparison (prevents timing attacks)
        - Never log plain_password or hashed_password
        - Returns False on invalid hash format (no exception raised)

    Reference:
        research.md lines 1306-1450 (Password verification)
    """
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        # Invalid hash format or verification error
        logger.error(f"Password verification error: {e}")
        return False


def create_access_token(user_id: str, email: str) -> str:
    """
    Create JWT access token for authenticated user.

    Token contains user_id, email, and expiration timestamp.
    Token expires in 24 hours (ACCESS_TOKEN_EXPIRE_HOURS).

    JWT Claims:
        - sub: User ID (subject)
        - email: User email address
        - exp: Expiration timestamp (UTC)
        - iat: Issued at timestamp (UTC)

    Args:
        user_id: Unique user identifier (UUID as string)
        email: User email address

    Returns:
        str: JWT token string (use in Authorization: Bearer header)

    Example:
        >>> token = create_access_token(
        ...     user_id="user_123",
        ...     email="user@example.com"
        ... )
        >>> print(token)
        'eyJhbGc...'  # JWT token

    Security Notes:
        - Token is signed with JWT_SECRET_KEY (verify on subsequent requests)
        - Expiration is enforced by JWT library (exp claim)
        - Never log the token value (treat as sensitive credential)
        - Use HTTPS for transmission to prevent interception

    Usage:
        # Create token on successful login/registration
        token = create_access_token(user.id, user.email)

        # Return to client
        return {"access_token": token, "token_type": "bearer"}

        # Client sends in Authorization header:
        # Authorization: Bearer eyJhbGc...

    Reference:
        research.md lines 1451-1600 (JWT authentication)
        tasks.md T098 (Account registration endpoint)
    """
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    to_encode = {
        "sub": user_id,          # Subject (user ID)
        "email": email,          # User email
        "exp": expire,           # Expiration timestamp
        "iat": datetime.utcnow() # Issued at timestamp
    }

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    logger.debug(
        f"Created access token for user {user_id} "
        f"(expires in {ACCESS_TOKEN_EXPIRE_HOURS} hours)"
    )

    return encoded_jwt


def create_signup_token(
    email: str,
    meal_plan_id: Optional[str] = None,
    payment_id: Optional[str] = None
) -> str:
    """
    Create signup token for account creation link in delivery email.

    Token is a signed JWT that encodes the purchase email and optional context.
    Token expires in 7 days (SIGNUP_TOKEN_EXPIRE_DAYS).

    This token allows users to create an account from the delivery email link,
    with the email pre-filled and readonly (per FR-R-001).

    JWT Claims:
        - email: Normalized email address (for account creation)
        - meal_plan_id: Associated meal plan ID (optional, for context)
        - payment_id: Associated payment ID (optional, for audit trail)
        - exp: Expiration timestamp (UTC)
        - iat: Issued at timestamp (UTC)
        - type: Token type ("signup")

    Args:
        email: User email address (will be normalized)
        meal_plan_id: Optional meal plan ID to associate with account
        payment_id: Optional payment ID for audit trail

    Returns:
        str: Signed JWT token for account creation URL

    Example:
        >>> token = create_signup_token(
        ...     email="user@example.com",
        ...     meal_plan_id="plan_123",
        ...     payment_id="txn_456"
        ... )
        >>> print(token)
        'eyJhbGc...'  # JWT token

        # Use in email link:
        # https://yourdomain.com/create-account?token=eyJhbGc...

    Security Notes:
        - Token is signed with JWT_SECRET_KEY (prevents tampering)
        - Email is normalized (prevents duplicate accounts)
        - Expires in 7 days (limits exposure window)
        - Single-use enforcement is NOT built into token (validate in endpoint)
        - Use HTTPS for email links to prevent token interception

    Reference:
        tasks.md T100 (Account creation link in delivery email)
        FR-R-001 (Email must match purchase email)
    """
    normalized_email = normalize_email(email)
    expire = datetime.utcnow() + timedelta(days=SIGNUP_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "email": normalized_email,
        "type": "signup",        # Token type (for validation)
        "exp": expire,           # Expiration timestamp
        "iat": datetime.utcnow() # Issued at timestamp
    }

    # Add optional context
    if meal_plan_id:
        to_encode["meal_plan_id"] = meal_plan_id
    if payment_id:
        to_encode["payment_id"] = payment_id

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    logger.debug(
        f"Created signup token for {normalized_email} "
        f"(expires in {SIGNUP_TOKEN_EXPIRE_DAYS} days)"
    )

    return encoded_jwt


def verify_signup_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode signup token from account creation link.

    Validates JWT signature, expiration, and token type.
    Returns decoded payload on success, None on failure.

    Args:
        token: JWT token from account creation URL

    Returns:
        Dict with decoded claims on success:
        - email: Normalized email address
        - meal_plan_id: Associated meal plan ID (if present)
        - payment_id: Associated payment ID (if present)
        - exp: Expiration timestamp
        - iat: Issued at timestamp

        None on failure (invalid signature, expired, wrong type)

    Example:
        >>> token = create_signup_token(email="user@example.com")
        >>> payload = verify_signup_token(token)
        >>> if payload:
        ...     print(f"Email: {payload['email']}")
        ...     print(f"Expires: {payload['exp']}")
        ... else:
        ...     print("Invalid or expired token")

    Error Cases:
        - Invalid signature: Returns None (token was tampered with)
        - Expired token: Returns None (token is past exp timestamp)
        - Wrong token type: Returns None (not a signup token)
        - Malformed token: Returns None (invalid JWT format)

    Security Notes:
        - Uses constant-time signature verification (via python-jose)
        - Checks token type to prevent using access tokens for signup
        - Logs verification failures for security monitoring
        - Never logs the token value itself

    Reference:
        tasks.md T098 (Account registration with signup token validation)
        FR-R-001 (Email must match purchase email)
    """
    try:
        # Decode and verify JWT
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Validate token type
        if payload.get("type") != "signup":
            logger.warning(
                f"Invalid token type for signup: {payload.get('type')} "
                f"(expected 'signup')"
            )
            return None

        logger.debug(f"Verified signup token for {payload.get('email')}")
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Signup token expired")
        return None
    except JWTError as e:
        logger.warning(f"Invalid signup token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying signup token: {e}")
        return None


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode access token from Authorization header.

    Validates JWT signature and expiration.
    Returns decoded payload on success, None on failure.

    Args:
        token: JWT token from Authorization: Bearer header

    Returns:
        Dict with decoded claims on success:
        - sub: User ID
        - email: User email
        - exp: Expiration timestamp
        - iat: Issued at timestamp

        None on failure (invalid signature, expired)

    Example:
        >>> token = create_access_token(user_id="user_123", email="user@example.com")
        >>> payload = verify_access_token(token)
        >>> if payload:
        ...     print(f"User ID: {payload['sub']}")
        ...     print(f"Email: {payload['email']}")
        ... else:
        ...     print("Invalid or expired token")

    Error Cases:
        - Invalid signature: Returns None (token was tampered with)
        - Expired token: Returns None (token is past exp timestamp)
        - Malformed token: Returns None (invalid JWT format)

    Security Notes:
        - Uses constant-time signature verification (via python-jose)
        - Checks expiration automatically (exp claim)
        - Logs verification failures for security monitoring
        - Never logs the token value itself

    Usage:
        # In FastAPI dependency
        from fastapi import Depends, HTTPException
        from fastapi.security import HTTPBearer

        security = HTTPBearer()

        async def get_current_user(token: str = Depends(security)):
            payload = verify_access_token(token.credentials)
            if not payload:
                raise HTTPException(401, "Invalid or expired token")
            return payload

    Reference:
        research.md lines 1451-1600 (JWT authentication)
    """
    try:
        # Decode and verify JWT
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        logger.debug(f"Verified access token for user {payload.get('sub')}")
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Access token expired")
        return None
    except JWTError as e:
        logger.warning(f"Invalid access token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying access token: {e}")
        return None
