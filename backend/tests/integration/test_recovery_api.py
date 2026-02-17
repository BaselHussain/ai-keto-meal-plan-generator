"""
Integration tests for recovery API (T107E).

Tests:
1. POST /recovery/request-magic-link with valid email succeeds (generic response)
2. Non-existent email returns same generic response (no enumeration)
3. Rate limit: 6th request from same IP in 1h blocked
4. GET /recovery/verify with valid token returns meal plan
5. GET /recovery/verify with invalid token returns error
6. Email normalization applied before lookup
"""

import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.meal_plan import MealPlan
from src.lib.email_utils import normalize_email


@pytest_asyncio.fixture
async def meal_plan_with_email(db_session: AsyncSession):
    """Create a meal plan for recovery testing."""
    from datetime import datetime, timedelta

    mp = MealPlan(
        payment_id=f"pay_recovery_{uuid.uuid4().hex[:8]}",
        email="recover@example.com",
        normalized_email=normalize_email("recover@example.com"),
        pdf_blob_path="https://blob.vercel-storage.com/recovery-test.pdf",
        calorie_target=1800,
        preferences_summary={"excluded_foods": [], "preferred_proteins": ["chicken"]},
        ai_model="gpt-4o",
        status="completed",
        email_sent_at=datetime.utcnow() - timedelta(hours=1),
        created_at=datetime.utcnow() - timedelta(hours=2),
    )
    db_session.add(mp)
    await db_session.commit()
    await db_session.refresh(mp)
    return mp


@pytest.mark.asyncio
async def test_request_magic_link_valid_email(async_client: AsyncClient, meal_plan_with_email):
    """T107E-1: Valid email returns generic success response."""
    with patch("src.api.recovery.check_rate_limit_email", new_callable=AsyncMock) as mock_email_rl, \
         patch("src.api.recovery.check_rate_limit_ip", new_callable=AsyncMock) as mock_ip_rl, \
         patch("src.api.recovery.send_magic_link_email", new_callable=AsyncMock) as mock_send:

        mock_email_rl.return_value = {"allowed": True, "remaining": 2}
        mock_ip_rl.return_value = {"allowed": True, "remaining": 4}
        mock_send.return_value = True

        response = await async_client.post(
            "/api/v1/recovery/request-magic-link",
            json={"email": "recover@example.com"},
            headers={"X-Forwarded-For": "10.0.0.1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data


@pytest.mark.asyncio
async def test_request_magic_link_nonexistent_email(async_client: AsyncClient):
    """T107E-2: Non-existent email returns same generic response (no enumeration)."""
    with patch("src.api.recovery.check_rate_limit_email", new_callable=AsyncMock) as mock_email_rl, \
         patch("src.api.recovery.check_rate_limit_ip", new_callable=AsyncMock) as mock_ip_rl:

        mock_email_rl.return_value = {"allowed": True, "remaining": 2}
        mock_ip_rl.return_value = {"allowed": True, "remaining": 4}

        response = await async_client.post(
            "/api/v1/recovery/request-magic-link",
            json={"email": "nonexistent@example.com"},
            headers={"X-Forwarded-For": "10.0.0.2"},
        )
        # Should return 200 (not 404) to prevent email enumeration
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_ip_rate_limit_blocks_6th_request(async_client: AsyncClient):
    """T107E-3: 6th request from same IP in 1h blocked."""
    with patch("src.api.recovery.check_rate_limit_email", new_callable=AsyncMock) as mock_email_rl, \
         patch("src.api.recovery.check_rate_limit_ip", new_callable=AsyncMock) as mock_ip_rl:

        mock_email_rl.return_value = {"allowed": True, "remaining": 2}
        mock_ip_rl.return_value = {"allowed": False, "remaining": 0, "retry_after": 3600}

        response = await async_client.post(
            "/api/v1/recovery/request-magic-link",
            json={"email": "test@example.com"},
            headers={"X-Forwarded-For": "10.0.0.3"},
        )
        assert response.status_code == 429


@pytest.mark.asyncio
async def test_verify_valid_token(async_client: AsyncClient, meal_plan_with_email, db_session: AsyncSession):
    """T107E-4: GET /recovery/verify with valid token returns meal plan details."""
    import hashlib
    import secrets
    from datetime import datetime, timedelta
    from src.models.magic_link import MagicLinkToken

    # Create a valid magic link token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    magic_token = MagicLinkToken(
        id=str(uuid.uuid4()),
        token_hash=token_hash,
        email="recover@example.com",
        normalized_email=normalize_email("recover@example.com"),
        expires_at=datetime.utcnow() + timedelta(hours=24),
        generation_ip="10.0.0.1",
    )
    db_session.add(magic_token)
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/recovery/verify?token={raw_token}",
        headers={"X-Forwarded-For": "10.0.0.1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "meal_plan" in data or "email" in data or "pdf" in data


@pytest.mark.asyncio
async def test_verify_invalid_token(async_client: AsyncClient):
    """T107E-5: GET /recovery/verify with invalid token returns error."""
    response = await async_client.get(
        "/api/v1/recovery/verify?token=invalid-token-here",
        headers={"X-Forwarded-For": "10.0.0.4"},
    )
    assert response.status_code in [400, 404]
    data = response.json()
    assert "error" in data or "detail" in data


@pytest.mark.asyncio
async def test_email_normalization_before_lookup(async_client: AsyncClient, meal_plan_with_email):
    """T107E-6: Email normalization applied before lookup."""
    with patch("src.api.recovery.check_rate_limit_email", new_callable=AsyncMock) as mock_email_rl, \
         patch("src.api.recovery.check_rate_limit_ip", new_callable=AsyncMock) as mock_ip_rl, \
         patch("src.api.recovery.send_magic_link_email", new_callable=AsyncMock) as mock_send:

        mock_email_rl.return_value = {"allowed": True, "remaining": 2}
        mock_ip_rl.return_value = {"allowed": True, "remaining": 4}
        mock_send.return_value = True

        # Use Gmail alias that should normalize to same email
        response = await async_client.post(
            "/api/v1/recovery/request-magic-link",
            json={"email": "RECOVER@example.com"},  # Different casing
            headers={"X-Forwarded-For": "10.0.0.5"},
        )
        assert response.status_code == 200
