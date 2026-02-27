"""
Integration tests for magic link verification (T094-T096).

Tests the complete magic link verification flow:
- Token validation and meal plan retrieval
- Single-use enforcement (T095)
- IP address logging and mismatch warnings (T096)
- Token expiration handling
- Error responses for invalid/expired/used tokens

Reference:
    Phase 7.2 - Magic link verification (T094-T096)
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.lib.database import get_db
from src.models.magic_link import MagicLinkToken
from src.models.meal_plan import MealPlan
from src.services.magic_link import generate_magic_link_token, verify_magic_link_token
from src.lib.email_utils import normalize_email


# Test client fixture
@pytest_asyncio.fixture
async def client(test_session: AsyncSession):
    """Create async test client for API requests with database override."""
    # Override database dependency to use test session
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    # Create async client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    # Clean up override
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_magic_link_verification_success(test_session):
    """
    Test successful magic link verification (T094).

    Verifies that a valid token returns meal plan details and marks token as used.
    """
    # Use a unique email to avoid collision with other tests that use test@example.com.
    # The shared in-memory SQLite DB accumulates committed records across tests,
    # so verify_magic_link_token would return multiple meal plans for a shared email.
    import uuid
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"verify_success_{unique_suffix}@example.com"
    normalized_email = normalize_email(email)

    meal_plan = MealPlan(
        payment_id=f"txn_test_verification_{unique_suffix}",
        email=email,
        normalized_email=normalized_email,
        pdf_blob_path="meal-plans/test_verification_001.pdf",
        calorie_target=1650,
        preferences_summary={
            "excluded_foods": ["beef"],
            "preferred_proteins": ["chicken"],
            "dietary_restrictions": "None"
        },
        ai_model="gpt-4o",
        status="completed",
    )
    test_session.add(meal_plan)
    await test_session.commit()

    # Generate magic link token
    token, token_record = await generate_magic_link_token(
        email=email,
        ip_address="192.168.1.1",
        db=test_session,
    )

    # Verify token
    verified_record, meal_plan_ids = await verify_magic_link_token(
        token=token,
        ip_address="192.168.1.2",  # Different IP
        db=test_session,
    )

    # Assertions
    assert verified_record is not None
    assert verified_record.email == email
    assert verified_record.normalized_email == normalized_email
    assert len(meal_plan_ids) == 1
    assert meal_plan_ids[0] == meal_plan.id

    # Check token was marked as used
    await test_session.refresh(token_record)
    assert token_record.used_at is not None
    assert token_record.usage_ip == "192.168.1.2"


@pytest.mark.asyncio
async def test_magic_link_single_use_enforcement(test_session):
    """
    Test single-use enforcement (T095).

    Verifies that a token can only be used once, and subsequent attempts
    are rejected with appropriate error.
    """
    # Setup: Create meal plan
    email = "singleuse@example.com"
    normalized_email = normalize_email(email)

    meal_plan = MealPlan(
        payment_id="txn_test_singleuse_001",
        email=email,
        normalized_email=normalized_email,
        pdf_blob_path="meal-plans/test_singleuse_001.pdf",
        calorie_target=1650,
        preferences_summary={
            "excluded_foods": [],
            "preferred_proteins": ["fish"],
            "dietary_restrictions": "None"
        },
        ai_model="gpt-4o",
        status="completed",
    )
    test_session.add(meal_plan)
    await test_session.commit()

    # Generate magic link token
    token, token_record = await generate_magic_link_token(
        email=email,
        ip_address="192.168.1.1",
        db=test_session,
    )

    # First verification - should succeed
    verified_record_1, meal_plan_ids_1 = await verify_magic_link_token(
        token=token,
        ip_address="192.168.1.1",
        db=test_session,
    )
    assert verified_record_1 is not None
    assert len(meal_plan_ids_1) == 1

    # Second verification - should fail (token already used)
    verified_record_2, meal_plan_ids_2 = await verify_magic_link_token(
        token=token,
        ip_address="192.168.1.1",
        db=test_session,
    )
    assert verified_record_2 is None
    assert meal_plan_ids_2 == []

    # Verify token is marked as used
    await test_session.refresh(token_record)
    assert token_record.used_at is not None


@pytest.mark.asyncio
async def test_magic_link_ip_logging(test_session, caplog):
    """
    Test IP address logging (T096).

    Verifies that generation_ip and usage_ip are logged, and that
    IP mismatches generate warnings (but don't block the request).
    """
    # Setup: Create meal plan
    email = "iplogging@example.com"
    normalized_email = normalize_email(email)

    meal_plan = MealPlan(
        payment_id="txn_test_iplogging_001",
        email=email,
        normalized_email=normalized_email,
        pdf_blob_path="meal-plans/test_iplogging_001.pdf",
        calorie_target=1650,
        preferences_summary={
            "excluded_foods": [],
            "preferred_proteins": ["chicken"],
            "dietary_restrictions": "None"
        },
        ai_model="gpt-4o",
        status="completed",
    )
    test_session.add(meal_plan)
    await test_session.commit()

    # Generate token with one IP
    generation_ip = "192.168.1.100"
    token, token_record = await generate_magic_link_token(
        email=email,
        ip_address=generation_ip,
        db=test_session,
    )

    # Verify token with different IP
    usage_ip = "10.0.0.50"
    with caplog.at_level("WARNING"):
        verified_record, meal_plan_ids = await verify_magic_link_token(
            token=token,
            ip_address=usage_ip,
            db=test_session,
        )

    # Verification should succeed despite IP mismatch
    assert verified_record is not None
    assert len(meal_plan_ids) == 1

    # Check IPs are logged
    await test_session.refresh(token_record)
    assert token_record.generation_ip == generation_ip
    assert token_record.usage_ip == usage_ip

    # Check warning was logged for IP mismatch
    assert any("IP mismatch" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_magic_link_expired_token(test_session):
    """
    Test expired token handling (T094).

    Verifies that expired tokens are rejected and marked as used to prevent replay.
    """
    # Setup: Create meal plan
    email = "expired@example.com"
    normalized_email = normalize_email(email)

    meal_plan = MealPlan(
        payment_id="txn_test_expired_001",
        email=email,
        normalized_email=normalized_email,
        pdf_blob_path="meal-plans/test_expired_001.pdf",
        calorie_target=1650,
        preferences_summary={
            "excluded_foods": [],
            "preferred_proteins": ["fish"],
            "dietary_restrictions": "None"
        },
        ai_model="gpt-4o",
        status="completed",
    )
    test_session.add(meal_plan)
    await test_session.commit()

    # Generate token
    token, token_record = await generate_magic_link_token(
        email=email,
        ip_address="192.168.1.1",
        db=test_session,
    )

    # Manually expire the token
    token_record.expires_at = datetime.utcnow() - timedelta(hours=1)
    await test_session.commit()

    # Try to verify expired token
    verified_record, meal_plan_ids = await verify_magic_link_token(
        token=token,
        ip_address="192.168.1.1",
        db=test_session,
    )

    # Should fail
    assert verified_record is None
    assert meal_plan_ids == []

    # Token should be marked as used to prevent replay
    await test_session.refresh(token_record)
    assert token_record.used_at is not None


@pytest.mark.asyncio
async def test_magic_link_invalid_token(test_session):
    """
    Test invalid token handling (T094).

    Verifies that non-existent tokens are rejected.
    """
    # Try to verify a token that doesn't exist
    verified_record, meal_plan_ids = await verify_magic_link_token(
        token="invalid_token_that_does_not_exist",
        ip_address="192.168.1.1",
        db=test_session,
    )

    # Should fail
    assert verified_record is None
    assert meal_plan_ids == []


@pytest.mark.asyncio
async def test_magic_link_no_meal_plans(test_session):
    """
    Test verification when no meal plans exist for the email (T094).

    This is a rare edge case (token exists but no meal plans).
    """
    # Generate token for email without meal plan
    email = "nomealplan@example.com"
    token, token_record = await generate_magic_link_token(
        email=email,
        ip_address="192.168.1.1",
        db=test_session,
    )

    # Verify token
    verified_record, meal_plan_ids = await verify_magic_link_token(
        token=token,
        ip_address="192.168.1.1",
        db=test_session,
    )

    # Token should verify (valid, not expired, not used)
    # But no meal plans returned
    assert verified_record is not None
    assert meal_plan_ids == []

    # Token should still be marked as used
    await test_session.refresh(token_record)
    assert token_record.used_at is not None


@pytest.mark.asyncio
async def test_magic_link_verification_endpoint(client, test_session):
    """
    Test magic link verification API endpoint (T094).

    Integration test for GET /api/v1/recovery/verify endpoint.
    """
    # Setup: Create meal plan
    email = "apitest@example.com"
    normalized_email = normalize_email(email)

    meal_plan = MealPlan(
        payment_id="txn_test_api_001",
        email=email,
        normalized_email=normalized_email,
        pdf_blob_path="meal-plans/test_api_001.pdf",
        calorie_target=1650,
        preferences_summary={
            "excluded_foods": [],
            "preferred_proteins": ["chicken"],
            "dietary_restrictions": "None"
        },
        ai_model="gpt-4o",
        status="completed",
    )
    test_session.add(meal_plan)
    await test_session.commit()

    # Generate magic link token
    token, token_record = await generate_magic_link_token(
        email=email,
        ip_address="192.168.1.1",
        db=test_session,
    )

    # Call API endpoint
    response = await client.get(f"/api/v1/recovery/verify?token={token}")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["meal_plan_id"] == meal_plan.id
    assert data["email"] == email
    assert data["pdf_available"] is True

    # Token should be marked as used
    await test_session.refresh(token_record)
    assert token_record.used_at is not None


@pytest.mark.asyncio
async def test_magic_link_verification_endpoint_already_used(client, test_session):
    """
    Test API endpoint with already-used token (T095).
    """
    # Setup: Create meal plan
    email = "alreadyused@example.com"
    normalized_email = normalize_email(email)

    meal_plan = MealPlan(
        payment_id="txn_test_used_001",
        email=email,
        normalized_email=normalized_email,
        pdf_blob_path="meal-plans/test_used_001.pdf",
        calorie_target=1650,
        preferences_summary={
            "excluded_foods": [],
            "preferred_proteins": ["fish"],
            "dietary_restrictions": "None"
        },
        ai_model="gpt-4o",
        status="completed",
    )
    test_session.add(meal_plan)
    await test_session.commit()

    # Generate and use token
    token, token_record = await generate_magic_link_token(
        email=email,
        ip_address="192.168.1.1",
        db=test_session,
    )
    await verify_magic_link_token(token=token, ip_address="192.168.1.1", db=test_session)

    # Try to use token again via API
    response = await client.get(f"/api/v1/recovery/verify?token={token}")

    # Should return 400 with TOKEN_ALREADY_USED error
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "bad_request"  # Status code 400 maps to bad_request
    assert "already been used" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_magic_link_verification_endpoint_expired(client, test_session):
    """
    Test API endpoint with expired token (T094).
    """
    # Setup: Create meal plan
    email = "expired_api@example.com"
    normalized_email = normalize_email(email)

    meal_plan = MealPlan(
        payment_id="txn_test_expired_api_001",
        email=email,
        normalized_email=normalized_email,
        pdf_blob_path="meal-plans/test_expired_api_001.pdf",
        calorie_target=1650,
        preferences_summary={
            "excluded_foods": [],
            "preferred_proteins": ["chicken"],
            "dietary_restrictions": "None"
        },
        ai_model="gpt-4o",
        status="completed",
    )
    test_session.add(meal_plan)
    await test_session.commit()

    # Generate token and manually expire it
    token, token_record = await generate_magic_link_token(
        email=email,
        ip_address="192.168.1.1",
        db=test_session,
    )
    token_record.expires_at = datetime.utcnow() - timedelta(hours=1)
    await test_session.commit()

    # Try to verify expired token via API
    response = await client.get(f"/api/v1/recovery/verify?token={token}")

    # Should return 400 with TOKEN_EXPIRED error
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "bad_request"
    assert "expired" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_magic_link_verification_endpoint_invalid_token(client, test_session):
    """
    Test API endpoint with invalid token (T094).
    """
    # Try to verify a non-existent token
    response = await client.get("/api/v1/recovery/verify?token=invalid_token")

    # Should return 400 with TOKEN_INVALID error
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "bad_request"
    assert "invalid" in data["error"]["message"].lower()
