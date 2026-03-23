"""
Unit tests for authentication endpoints (registration and login).

Tests account registration and login functionality including:
- T098: Account registration endpoint with email + password
- T100: Signup token validation (email from delivery link)
- T101: Email must match signup token (FR-R-001)
- Login endpoint with password verification
- Rate limiting on registration and login
- Email normalization and duplicate detection
- Password hashing and verification
- JWT token generation

Reference:
    tasks.md T098 (Account registration endpoint)
    tasks.md T100 (Account creation link in delivery email)
    tasks.md T101 (Enforce email match with signup token)
    FR-R-001 (Email must match purchase email)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def bypass_rate_limiting():
    """
    Bypass Redis-backed rate limiting for all tests in this module.

    The rate limiter accumulates counts in the real Redis instance.  Without
    this fixture every test beyond the configured threshold (5 register / 5
    login requests per window) would receive 429 Too Many Requests, making
    repeatable test runs impossible without flushing Redis between runs.
    """
    with patch("src.api.auth.check_rate_limit_ip", new_callable=AsyncMock) as mock_rl:
        mock_rl.return_value = None  # No-op: never raise RateLimitExceeded
        yield mock_rl

from src.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_signup_token,
    verify_signup_token,
)


# =============================================================================
# Password Hashing Tests
# =============================================================================


def test_hash_password():
    """Test password is hashed correctly with bcrypt."""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    # Hash should be different from password
    assert hashed != password

    # Hash should be bcrypt format (starts with $2b$)
    assert hashed.startswith("$2b$")

    # Hash should be 60 characters (bcrypt format)
    assert len(hashed) == 60


def test_hash_password_different_salts():
    """Test same password produces different hashes (due to salting)."""
    password = "SecurePassword123!"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    # Hashes should be different (different salts)
    assert hash1 != hash2

    # Both should verify correctly
    assert verify_password(password, hash1)
    assert verify_password(password, hash2)


def test_verify_password_correct():
    """Test password verification with correct password."""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    # Correct password should verify
    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Test password verification with incorrect password."""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    # Incorrect password should not verify
    assert verify_password("WrongPassword", hashed) is False
    assert verify_password("securepassword123!", hashed) is False  # Case sensitive


def test_verify_password_invalid_hash():
    """Test password verification with invalid hash format."""
    password = "SecurePassword123!"
    invalid_hash = "not_a_valid_bcrypt_hash"

    # Should return False (not raise exception)
    assert verify_password(password, invalid_hash) is False


# =============================================================================
# JWT Token Tests
# =============================================================================


def test_create_access_token():
    """Test JWT access token creation."""
    user_id = "user_123"
    email = "user@example.com"

    token = create_access_token(user_id, email)

    # Token should be non-empty string
    assert isinstance(token, str)
    assert len(token) > 0

    # Token should have 3 parts (header.payload.signature)
    assert token.count(".") == 2


def test_create_access_token_contains_claims():
    """Test JWT access token contains correct claims."""
    from jose import jwt
    from src.services.auth_service import JWT_SECRET_KEY

    user_id = "user_123"
    email = "user@example.com"
    token = create_access_token(user_id, email)

    # Decode token (without verification for testing)
    decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])

    # Check claims
    assert decoded["sub"] == user_id
    assert decoded["email"] == email
    assert "exp" in decoded
    assert "iat" in decoded


def test_create_signup_token():
    """Test signup token creation for account creation link."""
    email = "user@example.com"
    meal_plan_id = "plan_123"
    payment_id = "txn_456"

    token = create_signup_token(
        email=email,
        meal_plan_id=meal_plan_id,
        payment_id=payment_id
    )

    # Token should be non-empty string
    assert isinstance(token, str)
    assert len(token) > 0

    # Token should have 3 parts (header.payload.signature)
    assert token.count(".") == 2


def test_create_signup_token_normalizes_email():
    """Test signup token normalizes email (Gmail aliases)."""
    # Test Gmail normalization (dots and plus-suffix)
    token1 = create_signup_token("User.Name+tag@Gmail.com")
    token2 = create_signup_token("username@gmail.com")

    # Verify both tokens decode to same normalized email
    payload1 = verify_signup_token(token1)
    payload2 = verify_signup_token(token2)

    assert payload1 is not None
    assert payload2 is not None
    assert payload1["email"] == payload2["email"]
    assert payload1["email"] == "username@gmail.com"


def test_verify_signup_token_valid():
    """Test signup token verification with valid token."""
    email = "user@example.com"
    meal_plan_id = "plan_123"
    payment_id = "txn_456"

    token = create_signup_token(
        email=email,
        meal_plan_id=meal_plan_id,
        payment_id=payment_id
    )

    # Verify token
    payload = verify_signup_token(token)

    # Check payload
    assert payload is not None
    assert payload["email"] == email
    assert payload["meal_plan_id"] == meal_plan_id
    assert payload["payment_id"] == payment_id
    assert payload["type"] == "signup"
    assert "exp" in payload
    assert "iat" in payload


def test_verify_signup_token_expired():
    """Test signup token verification with expired token."""
    from jose import jwt
    from src.services.auth_service import JWT_SECRET_KEY as jwt_secret

    # Create expired token (expired 1 hour ago)
    expired_payload = {
        "email": "user@example.com",
        "type": "signup",
        "exp": datetime.utcnow() - timedelta(hours=1),
        "iat": datetime.utcnow() - timedelta(days=8),
    }
    expired_token = jwt.encode(expired_payload, jwt_secret, algorithm="HS256")

    # Verify should return None (expired)
    payload = verify_signup_token(expired_token)
    assert payload is None


def test_verify_signup_token_invalid_signature():
    """Test signup token verification with tampered signature."""
    token = create_signup_token("user@example.com")

    # Tamper with token (change last character)
    tampered_token = token[:-1] + ("A" if token[-1] != "A" else "B")

    # Verify should return None (invalid signature)
    payload = verify_signup_token(tampered_token)
    assert payload is None


def test_verify_signup_token_wrong_type():
    """Test signup token verification rejects access tokens."""
    # Create access token (not signup token)
    access_token = create_access_token("user_123", "user@example.com")

    # Verify should return None (wrong type)
    payload = verify_signup_token(access_token)
    assert payload is None


# =============================================================================
# Email Normalization Tests
# =============================================================================


def test_email_normalization_gmail():
    """Test email normalization for Gmail addresses."""
    from src.lib.email_utils import normalize_email

    # Test Gmail normalization (lowercase, remove dots, remove plus-suffix)
    assert normalize_email("User.Name+tag@Gmail.com") == "username@gmail.com"
    assert normalize_email("user.name@gmail.com") == "username@gmail.com"
    assert normalize_email("u.s.e.r@gmail.com") == "user@gmail.com"
    assert normalize_email("user+tag@gmail.com") == "user@gmail.com"
    assert normalize_email("user@googlemail.com") == "user@gmail.com"


def test_email_normalization_non_gmail():
    """Test email normalization for non-Gmail addresses."""
    from src.lib.email_utils import normalize_email

    # Test non-Gmail normalization (lowercase only, keep dots and plus)
    assert normalize_email("User.Name+tag@Example.com") == "user.name+tag@example.com"
    assert normalize_email("test@example.com") == "test@example.com"
    assert normalize_email("TEST@EXAMPLE.COM") == "test@example.com"


# =============================================================================
# Integration Tests (require database)
# =============================================================================


@pytest.mark.asyncio
async def test_register_endpoint_success(async_client, async_db):
    """Test account registration with valid email and password."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "auth_endpoint_test_unique@example.com",
            "password": "SecurePassword123!",
            "signup_token": None
        }
    )

    # Should succeed
    assert response.status_code == 201

    # Check response body
    data = response.json()
    assert data["access_token"] is not None
    assert data["token_type"] == "bearer"
    assert data["user_id"] is not None
    assert data["email"] == "auth_endpoint_test_unique@example.com"

    # Verify JWT token is valid
    from jose import jwt
    from src.services.auth_service import JWT_SECRET_KEY
    decoded = jwt.decode(data["access_token"], JWT_SECRET_KEY, algorithms=["HS256"])
    assert decoded["sub"] == data["user_id"]
    assert decoded["email"] == "auth_endpoint_test_unique@example.com"


@pytest.mark.asyncio
async def test_register_endpoint_duplicate_email(async_client, async_db):
    """Test account registration with duplicate email."""
    # First registration
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "SecurePassword123!",
            "signup_token": None
        }
    )

    # Second registration with same email
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "DifferentPassword456!",
            "signup_token": None
        }
    )

    # Should fail with 400 Bad Request
    assert response.status_code == 400
    assert "already exists" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_register_endpoint_with_signup_token(async_client, async_db):
    """Test account registration with valid signup token from delivery email."""
    # Create valid signup token
    email = "purchase@example.com"
    signup_token = create_signup_token(
        email=email,
        meal_plan_id="plan_123",
        payment_id="txn_456"
    )

    # Register with signup token
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123!",
            "signup_token": signup_token
        }
    )

    # Should succeed
    assert response.status_code == 201

    # Check response body
    data = response.json()
    assert data["email"] == email


@pytest.mark.asyncio
async def test_register_endpoint_signup_token_email_mismatch(async_client, async_db):
    """Test T101: Account email must match signup token email (FR-R-001)."""
    # Create signup token for one email
    signup_token = create_signup_token(
        email="original@example.com",
        meal_plan_id="plan_123",
        payment_id="txn_456"
    )

    # Try to register with different email
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "different@example.com",
            "password": "SecurePassword123!",
            "signup_token": signup_token
        }
    )

    # Should fail with 400 Bad Request (FR-R-001)
    assert response.status_code == 400
    assert "must match" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_register_endpoint_invalid_signup_token(async_client, async_db):
    """Test account registration with invalid signup token."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "signup_token": "invalid_token_format"
        }
    )

    # Should fail with 400 Bad Request
    assert response.status_code == 400
    assert "invalid" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_login_endpoint_success(async_client, async_db):
    """Test login with valid credentials."""
    # Register user first
    email = "loginuser@example.com"
    password = "SecurePassword123!"
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "signup_token": None
        }
    )

    # Login with correct credentials
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password
        }
    )

    # Should succeed
    assert response.status_code == 200

    # Check response body
    data = response.json()
    assert data["access_token"] is not None
    assert data["token_type"] == "bearer"
    assert data["user_id"] is not None
    assert data["email"] == email


@pytest.mark.asyncio
async def test_login_endpoint_invalid_email(async_client, async_db):
    """Test login with non-existent email."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "SomePassword123!"
        }
    )

    # Should fail with 401 Unauthorized (generic error to prevent user enumeration)
    assert response.status_code == 401
    assert "invalid" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_login_endpoint_invalid_password(async_client, async_db):
    """Test login with incorrect password."""
    # Register user first
    email = "passwordtest@example.com"
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "CorrectPassword123!",
            "signup_token": None
        }
    )

    # Login with wrong password
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "WrongPassword456!"
        }
    )

    # Should fail with 401 Unauthorized (generic error to prevent user enumeration)
    assert response.status_code == 401
    assert "invalid" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_login_endpoint_email_normalization(async_client, async_db):
    """Test login with Gmail email variations (normalization)."""
    # Register with normalized email
    normalized_email = "username@gmail.com"
    password = "SecurePassword123!"
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": normalized_email,
            "password": password,
            "signup_token": None
        }
    )

    # Login with Gmail alias (should normalize to same email)
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "User.Name+tag@Gmail.com",  # Should normalize to username@gmail.com
            "password": password
        }
    )

    # Should succeed (email normalized)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == normalized_email


@pytest.mark.asyncio
async def test_register_rate_limiting(async_client, async_db, bypass_rate_limiting):
    """Test rate limiting on registration endpoint (5 per IP per hour).

    This test verifies that the rate-limit path returns 429 when the limiter
    raises ``RateLimitExceeded``.  We use ``bypass_rate_limiting`` (autouse)
    to prevent Redis accumulation for all other tests, but here we override
    it to simulate the rate-limit being triggered on the 6th call.
    """
    from src.lib.rate_limiting import RateLimitExceeded

    call_count = 0

    async def _allow_then_block(ip_address, limit, window_seconds, operation="request"):
        nonlocal call_count
        call_count += 1
        if call_count > 5:
            raise RateLimitExceeded(
                "Too many register requests from your IP address. Please try again later.",
                limit=5,
                current_count=call_count,
            )

    bypass_rate_limiting.side_effect = _allow_then_block

    # Make 5 registration attempts (should all succeed or fail on duplicate)
    for i in range(5):
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": f"ratelimittest{i}@example.com",
                "password": "SecurePassword123!",
                "signup_token": None
            }
        )

    # 6th attempt should be rate limited (bypass_rate_limiting now raises)
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "ratelimittest6@example.com",
            "password": "SecurePassword123!",
            "signup_token": None
        }
    )

    # Should fail with 429 Too Many Requests
    assert response.status_code == 429
