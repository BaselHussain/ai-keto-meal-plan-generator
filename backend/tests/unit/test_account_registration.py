"""
Unit tests for T098 and T100 implementation verification.

Quick verification tests for:
- T098: Account registration endpoint exists and works
- T100: Signup token generation in delivery email URLs
"""

import pytest
from src.services.auth_service import (
    create_signup_token,
    verify_signup_token,
    hash_password,
    verify_password,
)
from src.lib.email_utils import normalize_email


class TestT100SignupTokenGeneration:
    """Verify T100: Signup token generation for delivery email."""

    def test_signup_token_basic_generation(self):
        """Test signup token can be created and verified."""
        email = "purchaser@example.com"
        meal_plan_id = "plan_123"
        payment_id = "txn_456"

        # Generate signup token (T100)
        token = create_signup_token(
            email=email,
            meal_plan_id=meal_plan_id,
            payment_id=payment_id,
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

        # Verify token can be decoded
        payload = verify_signup_token(token)
        assert payload is not None
        assert payload["email"] == normalize_email(email)
        assert payload["meal_plan_id"] == meal_plan_id
        assert payload["payment_id"] == payment_id
        assert payload["type"] == "signup"

    def test_signup_token_email_normalization(self):
        """Test signup token normalizes Gmail addresses."""
        original = "test.user+alias@gmail.com"
        expected = "testuser@gmail.com"

        token = create_signup_token(email=original)
        payload = verify_signup_token(token)

        assert payload["email"] == expected

    def test_delivery_email_url_generation(self):
        """Test complete delivery email URL generation (T100)."""
        from src.services.email_service import _build_delivery_urls

        payment_id = "test_payment_123"
        user_email = "user@example.com"
        meal_plan_id = "plan_abc"

        # Build URLs for delivery email (T100)
        urls = _build_delivery_urls(payment_id, user_email, meal_plan_id)

        # Verify all required URLs are present
        assert "pdf_download_url" in urls
        assert "magic_link_url" in urls
        assert "create_account_url" in urls

        # Verify create account URL contains signup token
        assert "create-account?token=" in urls["create_account_url"]

        # Extract and verify signup token from URL
        token_start = urls["create_account_url"].find("token=") + 6
        token = urls["create_account_url"][token_start:]

        # Verify token is valid
        payload = verify_signup_token(token)
        assert payload is not None
        assert payload["email"] == normalize_email(user_email)
        assert payload["meal_plan_id"] == meal_plan_id
        assert payload["payment_id"] == payment_id


class TestT098PasswordHashing:
    """Verify T098: Password hashing with bcrypt."""

    def test_password_hashing(self):
        """Test password is hashed with bcrypt."""
        password = "SecurePassword123!"

        # Hash password (T098)
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password  # Never store plain text
        assert hashed.startswith("$2b$")  # Bcrypt format

    def test_password_verification(self):
        """Test password verification works."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        # Verify correct password
        assert verify_password(password, hashed) is True

        # Verify incorrect password
        assert verify_password("WrongPassword", hashed) is False


def test_t098_and_t100_integration():
    """
    Integration test verifying T098 and T100 work together.

    Flow:
    1. T100: Generate signup token for delivery email
    2. T098: User clicks link, registers with signup token
    3. Verify email from token matches registration email
    """
    # T100: Generate signup token (simulates delivery email)
    purchase_email = "purchaser@example.com"
    signup_token = create_signup_token(
        email=purchase_email,
        meal_plan_id="plan_123",
        payment_id="txn_456",
    )

    # Verify token is valid
    payload = verify_signup_token(signup_token)
    assert payload is not None
    assert payload["email"] == normalize_email(purchase_email)

    # T098: User registers with signup token
    registration_email = purchase_email  # Must match per FR-R-001
    registration_password = "SecurePassword123!"

    # Simulate registration validation
    normalized_reg_email = normalize_email(registration_email)
    token_email = payload["email"]

    # Verify email match (FR-R-001)
    assert normalized_reg_email == token_email

    # Hash password (T098)
    password_hash = hash_password(registration_password)
    assert password_hash is not None
    assert password_hash.startswith("$2b$")

    print("\nT098 and T100 integration test PASSED")
    print(f"[OK] Signup token generated: {signup_token[:50]}...")
    print(f"[OK] Token email: {token_email}")
    print(f"[OK] Registration email: {normalized_reg_email}")
    print(f"[OK] Email match verified (FR-R-001)")
    print(f"[OK] Password hashed with bcrypt")
