"""
Unit tests for authentication service.

Tests password hashing, JWT token generation, and signup token validation.

Reference:
    tasks.md T098 (Account registration endpoint)
"""

import pytest
from datetime import datetime, timedelta

from src.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_signup_token,
    verify_signup_token,
    verify_access_token,
)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_creates_different_hashes(self):
        """Hash same password twice produces different hashes (salting works)."""
        password = "TestPassword123!"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different (bcrypt uses random salt)
        assert hash1 != hash2

        # Both hashes should verify the same password
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_verify_password_correct(self):
        """Verify password with correct password returns True."""
        password = "CorrectPassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Verify password with incorrect password returns False."""
        correct_password = "CorrectPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = hash_password(correct_password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_invalid_hash(self):
        """Verify password with invalid hash returns False (no exception)."""
        password = "TestPassword123!"
        invalid_hash = "not-a-valid-bcrypt-hash"

        # Should return False instead of raising exception
        assert verify_password(password, invalid_hash) is False


class TestAccessToken:
    """Test JWT access token generation and verification."""

    def test_create_access_token(self):
        """Create access token with user_id and email."""
        user_id = "user_123"
        email = "user@example.com"

        token = create_access_token(user_id=user_id, email=email)

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Token should contain JWT parts (header.payload.signature)
        assert token.count(".") == 2

    def test_verify_access_token_valid(self):
        """Verify valid access token returns payload."""
        user_id = "user_123"
        email = "user@example.com"

        token = create_access_token(user_id=user_id, email=email)
        payload = verify_access_token(token)

        # Payload should contain user_id and email
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["email"] == email

        # Payload should contain exp and iat timestamps
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_access_token_invalid(self):
        """Verify invalid token returns None."""
        invalid_token = "invalid.jwt.token"

        payload = verify_access_token(invalid_token)

        assert payload is None

    def test_verify_access_token_tampered(self):
        """Verify tampered token returns None."""
        user_id = "user_123"
        email = "user@example.com"

        token = create_access_token(user_id=user_id, email=email)

        # Tamper with the signature segment (third part after splitting on '.')
        # Replace the entire signature with a bogus value to guarantee failure.
        header, payload_part, _ = token.split(".")
        tampered_token = f"{header}.{payload_part}.invalidsignatureXXXXXXXXXXXXXX"

        result = verify_access_token(tampered_token)

        assert result is None


class TestSignupToken:
    """Test signup token generation and verification."""

    def test_create_signup_token(self):
        """Create signup token with email."""
        email = "user@example.com"

        token = create_signup_token(email=email)

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Token should contain JWT parts
        assert token.count(".") == 2

    def test_create_signup_token_with_context(self):
        """Create signup token with meal_plan_id and payment_id."""
        email = "user@example.com"
        meal_plan_id = "plan_123"
        payment_id = "txn_456"

        token = create_signup_token(
            email=email,
            meal_plan_id=meal_plan_id,
            payment_id=payment_id,
        )

        payload = verify_signup_token(token)

        assert payload is not None
        assert payload["email"] == email.lower()  # Email is normalized
        assert payload["meal_plan_id"] == meal_plan_id
        assert payload["payment_id"] == payment_id
        assert payload["type"] == "signup"

    def test_verify_signup_token_valid(self):
        """Verify valid signup token returns payload."""
        email = "user@example.com"

        token = create_signup_token(email=email)
        payload = verify_signup_token(token)

        # Payload should contain email and type
        assert payload is not None
        assert payload["email"] == email.lower()  # Email is normalized
        assert payload["type"] == "signup"

        # Payload should contain exp and iat timestamps
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_signup_token_invalid(self):
        """Verify invalid token returns None."""
        invalid_token = "invalid.jwt.token"

        payload = verify_signup_token(invalid_token)

        assert payload is None

    def test_verify_signup_token_wrong_type(self):
        """Verify access token as signup token returns None."""
        user_id = "user_123"
        email = "user@example.com"

        # Create access token (not signup token)
        access_token = create_access_token(user_id=user_id, email=email)

        # Try to verify as signup token
        payload = verify_signup_token(access_token)

        # Should return None (wrong token type)
        assert payload is None

    def test_verify_signup_token_tampered(self):
        """Verify tampered signup token returns None."""
        email = "user@example.com"

        token = create_signup_token(email=email)

        # Replace the signature segment entirely to guarantee verification failure.
        header, payload_part, _ = token.split(".")
        tampered_token = f"{header}.{payload_part}.invalidsignatureXXXXXXXXXXXXXX"

        payload = verify_signup_token(tampered_token)

        assert payload is None

    def test_email_normalization_in_signup_token(self):
        """Signup token normalizes email (lowercase, Gmail aliases)."""
        email = "User.Name+tag@Gmail.com"

        token = create_signup_token(email=email)
        payload = verify_signup_token(token)

        # Email should be normalized (lowercase, dots removed for Gmail)
        assert payload is not None
        assert payload["email"] == "username@gmail.com"
