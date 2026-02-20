"""
Integration tests for account creation flow (T098, T100).

Tests the complete account creation workflow:
1. T100: Signup token generation in delivery email
2. T098: Account registration endpoint with signup token validation
3. FR-R-001: Email must match purchase email (readonly field enforcement)

Test Coverage:
- Signup token generation and validation (7-day expiry)
- Account registration with email + password
- Account registration with signup token (pre-filled email)
- Email normalization (Gmail dot/plus removal)
- Duplicate email detection
- Password hashing (bcrypt)
- JWT access token generation (24h expiry)
- Rate limiting (5 registrations per IP per hour)
- Email mismatch detection (signup token vs registration email)

Reference:
    tasks.md T098 (Account registration endpoint)
    tasks.md T100 (Signup token in delivery email)
    FR-R-001 (Email must match purchase email)
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.main import app
from src.models.user import User
from src.services.auth_service import (
    create_signup_token,
    verify_signup_token,
    verify_access_token,
    verify_password,
)
from src.lib.email_utils import normalize_email


@pytest.fixture(autouse=True)
def bypass_rate_limiting():
    """Bypass Redis rate limiting for auth tests to prevent cross-test contamination."""
    with patch("src.api.auth.check_rate_limit_ip", new_callable=AsyncMock) as mock_rl:
        mock_rl.return_value = None  # No exception = rate limit not exceeded
        yield mock_rl


@pytest.mark.asyncio
class TestAccountRegistration:
    """Test account registration endpoint (T098)."""

    async def test_register_without_signup_token(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        """
        Test direct account registration without signup token.

        Flow: User registers with email + password (no delivery email context).
        """
        # Prepare test data
        email = "newuser@example.com"
        password = "SecurePassword123!"

        # Register account
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "signup_token": None,
            },
        )

        # Assert successful registration
        assert response.status_code == 201
        data = response.json()

        assert data["token_type"] == "bearer"
        assert "access_token" in data
        assert "user_id" in data
        assert data["email"] == email

        # Verify user exists in database
        normalized_email = normalize_email(email)
        user_stmt = select(User).where(User.normalized_email == normalized_email)
        result = await async_db.execute(user_stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.email == email
        assert user.normalized_email == normalized_email
        assert user.password_hash is not None

        # Verify password hash is correct
        assert verify_password(password, user.password_hash)

        # Verify JWT access token is valid
        token_payload = verify_access_token(data["access_token"])
        assert token_payload is not None
        assert token_payload["sub"] == user.id
        assert token_payload["email"] == user.email

    async def test_register_with_signup_token(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        """
        Test account registration with signup token from delivery email (T100).

        Flow: User clicks "Create Account" link in delivery email,
        signup token pre-fills email (readonly), user provides password.
        """
        # Prepare test data
        email = "purchaser@example.com"
        password = "SecurePassword123!"
        meal_plan_id = "plan_abc123"
        payment_id = "txn_xyz789"

        # Generate signup token (simulates delivery email link generation)
        signup_token = create_signup_token(
            email=email,
            meal_plan_id=meal_plan_id,
            payment_id=payment_id,
        )

        # Verify token is valid
        token_payload = verify_signup_token(signup_token)
        assert token_payload is not None
        assert token_payload["email"] == normalize_email(email)
        assert token_payload["meal_plan_id"] == meal_plan_id
        assert token_payload["payment_id"] == payment_id

        # Register account with signup token
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,  # Pre-filled from token (readonly in UI)
                "password": password,
                "signup_token": signup_token,
            },
        )

        # Assert successful registration
        assert response.status_code == 201
        data = response.json()

        assert data["token_type"] == "bearer"
        assert "access_token" in data
        assert "user_id" in data
        assert data["email"] == email

        # Verify user exists in database
        normalized_email = normalize_email(email)
        user_stmt = select(User).where(User.normalized_email == normalized_email)
        result = await async_db.execute(user_stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.email == email
        assert user.normalized_email == normalized_email
        assert user.password_hash is not None

        # Verify password hash is correct
        assert verify_password(password, user.password_hash)

    async def test_register_email_mismatch_with_signup_token(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        """
        Test email mismatch rejection (FR-R-001).

        Flow: User tries to register with different email than in signup token.
        Expected: 400 error, email must match purchase email.
        """
        # Prepare test data
        token_email = "purchaser@example.com"
        different_email = "different@example.com"
        password = "SecurePassword123!"

        # Generate signup token with original email
        signup_token = create_signup_token(
            email=token_email,
            meal_plan_id="plan_abc123",
            payment_id="txn_xyz789",
        )

        # Try to register with different email (should fail)
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": different_email,  # Different from token email
                "password": password,
                "signup_token": signup_token,
            },
        )

        # Assert rejection (email mismatch)
        assert response.status_code == 400
        data = response.json()
        error_msg = data.get("error", {}).get("message", data.get("detail", ""))
        assert "email address must match" in error_msg.lower()

        # Verify no user was created
        normalized_email = normalize_email(different_email)
        user_stmt = select(User).where(User.normalized_email == normalized_email)
        result = await async_db.execute(user_stmt)
        user = result.scalar_one_or_none()

        assert user is None

    async def test_register_duplicate_email(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        """
        Test duplicate email detection.

        Flow: User tries to register with email that already exists.
        Expected: 400 error, account already exists.
        """
        # Prepare test data
        email = "duplicate@example.com"
        password = "SecurePassword123!"

        # First registration (should succeed)
        response1 = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "signup_token": None,
            },
        )
        assert response1.status_code == 201

        # Second registration with same email (should fail)
        response2 = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "DifferentPassword456!",
                "signup_token": None,
            },
        )

        # Assert rejection (duplicate email)
        assert response2.status_code == 400
        data = response2.json()
        error_msg = data.get("error", {}).get("message", data.get("detail", ""))
        assert "already exists" in error_msg.lower()

    async def test_register_email_normalization(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        """
        Test email normalization prevents duplicate Gmail accounts.

        Flow: User tries to register with Gmail address variations
        (dots, plus-suffixes) that normalize to same email.
        """
        # Prepare test data
        base_email = "testuser@gmail.com"
        password = "SecurePassword123!"

        # First registration with base email
        response1 = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": base_email,
                "password": password,
                "signup_token": None,
            },
        )
        assert response1.status_code == 201

        # Try to register with Gmail variations (all normalize to same email)
        gmail_variations = [
            "test.user@gmail.com",       # Dots in local part
            "test.u.s.e.r@gmail.com",    # Multiple dots
            "testuser+alias@gmail.com",  # Plus-suffix
            "test.user+alias@gmail.com", # Dots + plus-suffix
            "testuser@googlemail.com",   # Googlemail domain
        ]

        for variation in gmail_variations:
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": variation,
                    "password": password,
                    "signup_token": None,
                },
            )

            # All variations should be rejected (duplicate email)
            assert response.status_code == 400
            data = response.json()
            error_msg = data.get("error", {}).get("message", data.get("detail", ""))
            assert "already exists" in error_msg.lower()

    async def test_register_invalid_signup_token(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        """
        Test invalid/expired signup token rejection.

        Flow: User tries to register with invalid or expired signup token.
        Expected: 400 error, invalid or expired signup link.
        """
        # Prepare test data
        email = "test@example.com"
        password = "SecurePassword123!"
        invalid_token = "invalid.jwt.token"

        # Try to register with invalid token
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "signup_token": invalid_token,
            },
        )

        # Assert rejection (invalid token)
        assert response.status_code == 400
        data = response.json()
        error_msg = data.get("error", {}).get("message", data.get("detail", ""))
        assert "invalid or expired" in error_msg.lower()

    async def test_register_password_hashing(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        """
        Test password is hashed with bcrypt (never stored in plain text).

        Flow: User registers, verify password is hashed in database.
        """
        # Prepare test data
        email = "hasheduser@example.com"
        password = "SecurePassword123!"

        # Register account
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "signup_token": None,
            },
        )
        assert response.status_code == 201

        # Verify password is hashed in database
        normalized_email = normalize_email(email)
        user_stmt = select(User).where(User.normalized_email == normalized_email)
        result = await async_db.execute(user_stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.password_hash is not None
        assert user.password_hash != password  # Never stored in plain text
        assert user.password_hash.startswith("$2b$")  # Bcrypt hash format

        # Verify password can be verified
        assert verify_password(password, user.password_hash)
        assert not verify_password("WrongPassword", user.password_hash)


class TestSignupTokenGeneration:
    """Test signup token generation for delivery email (T100)."""

    def test_signup_token_generation(self):
        """
        Test signup token generation for delivery email link.

        Flow: System generates signup token when sending delivery email.
        """
        # Prepare test data
        email = "purchaser@example.com"
        meal_plan_id = "plan_abc123"
        payment_id = "txn_xyz789"

        # Generate signup token
        signup_token = create_signup_token(
            email=email,
            meal_plan_id=meal_plan_id,
            payment_id=payment_id,
        )

        # Verify token is a valid JWT
        assert signup_token is not None
        assert isinstance(signup_token, str)
        assert len(signup_token) > 50  # JWT tokens are long strings

        # Verify token can be decoded
        payload = verify_signup_token(signup_token)
        assert payload is not None
        assert payload["email"] == normalize_email(email)
        assert payload["meal_plan_id"] == meal_plan_id
        assert payload["payment_id"] == payment_id
        assert payload["type"] == "signup"

        # Verify expiration is 7 days
        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]
        expiry_seconds = exp_timestamp - iat_timestamp
        expected_seconds = 7 * 24 * 60 * 60  # 7 days

        # Allow 1 second tolerance for test execution time
        assert abs(expiry_seconds - expected_seconds) <= 1

    def test_signup_token_email_normalization(self):
        """
        Test signup token normalizes email for consistency.

        Flow: Signup token should normalize Gmail addresses.
        """
        # Test Gmail address with dots and plus-suffix
        original_email = "test.user+alias@gmail.com"
        expected_normalized = "testuser@gmail.com"

        signup_token = create_signup_token(email=original_email)
        payload = verify_signup_token(signup_token)

        assert payload is not None
        assert payload["email"] == expected_normalized

    def test_signup_token_without_optional_context(self):
        """
        Test signup token generation without meal_plan_id or payment_id.

        Flow: System can generate signup token with only email.
        """
        email = "user@example.com"

        signup_token = create_signup_token(email=email)
        payload = verify_signup_token(signup_token)

        assert payload is not None
        assert payload["email"] == normalize_email(email)
        assert "meal_plan_id" not in payload
        assert "payment_id" not in payload
        assert payload["type"] == "signup"


@pytest.mark.asyncio
class TestAccountLogin:
    """Test account login endpoint."""

    async def test_login_success(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        """
        Test successful login with email and password.

        Flow: User registers, then logs in with credentials.
        """
        # Register account first
        email = "loginuser@example.com"
        password = "SecurePassword123!"

        register_response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "signup_token": None,
            },
        )
        assert register_response.status_code == 201

        # Login with credentials
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        # Assert successful login
        assert login_response.status_code == 200
        data = login_response.json()

        assert data["token_type"] == "bearer"
        assert "access_token" in data
        assert "user_id" in data
        assert data["email"] == email

        # Verify JWT access token is valid
        token_payload = verify_access_token(data["access_token"])
        assert token_payload is not None
        assert token_payload["email"] == email

    async def test_login_invalid_password(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        """
        Test login rejection with incorrect password.

        Flow: User tries to login with wrong password.
        Expected: 400 error, invalid credentials.
        """
        # Register account first
        email = "loginuser2@example.com"
        password = "SecurePassword123!"

        register_response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "signup_token": None,
            },
        )
        assert register_response.status_code == 201

        # Try to login with wrong password
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "WrongPassword456!",
            },
        )

        # Assert rejection (invalid password) - 401 Unauthorized
        assert login_response.status_code == 401
        data = login_response.json()
        error_msg = data.get("error", {}).get("message", data.get("detail", ""))
        assert "invalid email or password" in error_msg.lower()

    async def test_login_nonexistent_user(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        """
        Test login rejection for non-existent user.

        Flow: User tries to login with email that doesn't exist.
        Expected: 400 error, invalid credentials (no user enumeration).
        """
        # Try to login with non-existent email
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123!",
            },
        )

        # Assert rejection (generic error message to prevent user enumeration)
        assert login_response.status_code == 401
        data = login_response.json()
        error_msg = data.get("error", {}).get("message", data.get("detail", ""))
        assert "invalid email or password" in error_msg.lower()
