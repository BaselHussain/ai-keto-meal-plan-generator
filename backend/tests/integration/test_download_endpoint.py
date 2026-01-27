"""
Integration tests for download endpoint (T107).

Tests:
- Download with valid meal_plan_id
- Download with valid magic link token
- Download with invalid/expired token
- Rate limit enforcement (10 downloads per 24h)
- Grace period bypass (5 minutes after email delivery)
- PDF not available scenarios
- Error handling

Test Coverage:
- Authorization (magic link token verification)
- Rate limiting with Redis
- Signed URL generation
- Error responses (400, 401, 404, 429, 503)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from httpx import AsyncClient
from sqlalchemy import select

from src.models.meal_plan import MealPlan
from src.models.magic_link import MagicLinkToken
from src.lib.email_utils import normalize_email
from src.services.magic_link import generate_magic_link_token


class TestDownloadEndpoint:
    """Integration tests for /download/download-pdf endpoint."""

    @pytest.mark.asyncio
    async def test_download_missing_both_params(self, client: AsyncClient):
        """Test download request missing both meal_plan_id and token."""
        response = await client.get("/api/v1/download/download-pdf")

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "INVALID_REQUEST"
        assert "meal_plan_id or token" in data["detail"]["message"]

    @pytest.mark.asyncio
    async def test_download_with_invalid_meal_plan_id(self, client: AsyncClient):
        """Test download with non-existent meal_plan_id."""
        response = await client.get(
            "/api/v1/download/download-pdf",
            params={"meal_plan_id": "non-existent-id"}
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_download_with_valid_magic_link_token(
        self,
        client: AsyncClient,
        db_session,
        sample_meal_plan,
    ):
        """Test download with valid magic link token."""
        # Generate magic link token
        token, token_record = await generate_magic_link_token(
            email=sample_meal_plan.email,
            ip_address="192.168.1.1",
            db=db_session,
        )

        # Mock blob storage signed URL generation
        with patch("src.api.download.generate_signed_download_url") as mock_signed_url:
            mock_signed_url.return_value = "https://blob.vercel-storage.com/signed-url"

            response = await client.get(
                "/api/v1/download/download-pdf",
                params={"token": token}
            )

            assert response.status_code == 200
            data = response.json()
            assert "download_url" in data
            assert data["download_url"] == "https://blob.vercel-storage.com/signed-url"
            assert data["expires_in"] == 3600

            # Verify signed URL generation was called
            mock_signed_url.assert_called_once_with(
                blob_url=sample_meal_plan.pdf_blob_path,
                expiry_seconds=3600,
            )

    @pytest.mark.asyncio
    async def test_download_with_invalid_token(self, client: AsyncClient):
        """Test download with invalid magic link token."""
        response = await client.get(
            "/api/v1/download/download-pdf",
            params={"token": "invalid-token-abc123"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["code"] == "UNAUTHORIZED"
        assert "magic link" in data["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_download_with_expired_token(
        self,
        client: AsyncClient,
        db_session,
        sample_meal_plan,
    ):
        """Test download with expired magic link token."""
        # Create expired token (created 25 hours ago)
        import hashlib
        import secrets

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()

        expired_token = MagicLinkToken(
            token_hash=token_hash,
            email=sample_meal_plan.email,
            normalized_email=normalize_email(sample_meal_plan.email),
            created_at=datetime.utcnow() - timedelta(hours=25),
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
            generation_ip="192.168.1.1",
        )
        db_session.add(expired_token)
        await db_session.commit()

        response = await client.get(
            "/api/v1/download/download-pdf",
            params={"token": token}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["code"] == "UNAUTHORIZED"

    @pytest.mark.asyncio
    async def test_download_pdf_not_available_processing(
        self,
        client: AsyncClient,
        db_session,
        sample_meal_plan,
    ):
        """Test download when PDF is still processing."""
        # Set meal plan to processing status with no PDF
        sample_meal_plan.status = "processing"
        sample_meal_plan.pdf_blob_path = None
        await db_session.commit()

        # Generate magic link token
        token, _ = await generate_magic_link_token(
            email=sample_meal_plan.email,
            ip_address="192.168.1.1",
            db=db_session,
        )

        response = await client.get(
            "/api/v1/download/download-pdf",
            params={"token": token}
        )

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "PDF_NOT_AVAILABLE"
        assert "try again" in data["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_download_pdf_not_available_failed(
        self,
        client: AsyncClient,
        db_session,
        sample_meal_plan,
    ):
        """Test download when PDF generation failed."""
        # Set meal plan to failed status
        sample_meal_plan.status = "failed"
        sample_meal_plan.pdf_blob_path = None
        await db_session.commit()

        # Generate magic link token
        token, _ = await generate_magic_link_token(
            email=sample_meal_plan.email,
            ip_address="192.168.1.1",
            db=db_session,
        )

        response = await client.get(
            "/api/v1/download/download-pdf",
            params={"token": token}
        )

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "PDF_NOT_AVAILABLE"
        assert "contact support" in data["detail"]["message"].lower()


class TestDownloadRateLimitIntegration:
    """Integration tests for download rate limiting."""

    @pytest.mark.asyncio
    async def test_grace_period_bypass(
        self,
        client: AsyncClient,
        db_session,
        sample_meal_plan,
        redis_client,
    ):
        """Test downloads within 5 minutes bypass rate limit."""
        # Set email_sent_at to 2 minutes ago (within grace period)
        sample_meal_plan.email_sent_at = datetime.utcnow() - timedelta(minutes=2)
        await db_session.commit()

        # Generate magic link token
        token, _ = await generate_magic_link_token(
            email=sample_meal_plan.email,
            ip_address="192.168.1.1",
            db=db_session,
        )

        # Mock blob storage
        with patch("src.api.download.generate_signed_download_url") as mock_signed_url:
            mock_signed_url.return_value = "https://blob.vercel-storage.com/signed-url"

            # Make multiple downloads (should all succeed due to grace period)
            for i in range(15):  # More than the 10 download limit
                response = await client.get(
                    "/api/v1/download/download-pdf",
                    params={"token": token}
                )

                # All should succeed (grace period bypass)
                assert response.status_code == 200

        # Verify Redis counter was NOT incremented (grace period bypass)
        # Note: We need to check that the download_rate key doesn't exist or is 0
        normalized_email = normalize_email(sample_meal_plan.email)
        import hashlib
        combined = f"{normalized_email}:192.168.1.1"
        hash_value = hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16]
        rate_key = f"download_rate:guest:{hash_value}"

        # Key should not exist or be 0 (grace period bypass)
        count = await redis_client.get(rate_key)
        assert count is None or int(count) == 0

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(
        self,
        client: AsyncClient,
        db_session,
        sample_meal_plan,
        redis_client,
    ):
        """Test rate limit enforced after grace period."""
        # Set email_sent_at to 6 minutes ago (outside grace period)
        sample_meal_plan.email_sent_at = datetime.utcnow() - timedelta(minutes=6)
        await db_session.commit()

        # Generate magic link token
        token, _ = await generate_magic_link_token(
            email=sample_meal_plan.email,
            ip_address="192.168.1.1",
            db=db_session,
        )

        # Mock blob storage
        with patch("src.api.download.generate_signed_download_url") as mock_signed_url:
            mock_signed_url.return_value = "https://blob.vercel-storage.com/signed-url"

            # Make 10 downloads (should all succeed)
            for i in range(10):
                response = await client.get(
                    "/api/v1/download/download-pdf",
                    params={"token": token}
                )
                assert response.status_code == 200

            # 11th download should be rate limited
            response = await client.get(
                "/api/v1/download/download-pdf",
                params={"token": token}
            )

            assert response.status_code == 429
            data = response.json()
            assert data["detail"]["code"] == "RATE_LIMITED"
            assert "retry_after" in data["detail"]

    @pytest.mark.asyncio
    async def test_rate_limit_different_users_independent(
        self,
        client: AsyncClient,
        db_session,
        redis_client,
    ):
        """Test rate limits are independent for different users."""
        # Create two meal plans for different users
        from src.models.meal_plan import MealPlan

        meal_plan1 = MealPlan(
            payment_id="pay_001",
            email="user1@example.com",
            normalized_email=normalize_email("user1@example.com"),
            pdf_blob_path="https://blob.vercel-storage.com/plan1.pdf",
            calorie_target=1500,
            preferences_summary={"excluded_foods": []},
            ai_model="gpt-4o",
            status="completed",
            email_sent_at=datetime.utcnow() - timedelta(hours=1),  # Outside grace period
        )
        db_session.add(meal_plan1)

        meal_plan2 = MealPlan(
            payment_id="pay_002",
            email="user2@example.com",
            normalized_email=normalize_email("user2@example.com"),
            pdf_blob_path="https://blob.vercel-storage.com/plan2.pdf",
            calorie_target=1800,
            preferences_summary={"excluded_foods": []},
            ai_model="gpt-4o",
            status="completed",
            email_sent_at=datetime.utcnow() - timedelta(hours=1),  # Outside grace period
        )
        db_session.add(meal_plan2)
        await db_session.commit()

        # Generate tokens for both users
        token1, _ = await generate_magic_link_token(
            email=meal_plan1.email,
            ip_address="192.168.1.1",
            db=db_session,
        )
        token2, _ = await generate_magic_link_token(
            email=meal_plan2.email,
            ip_address="192.168.1.2",
            db=db_session,
        )

        # Mock blob storage
        with patch("src.api.download.generate_signed_download_url") as mock_signed_url:
            mock_signed_url.return_value = "https://blob.vercel-storage.com/signed-url"

            # User 1: Make 10 downloads
            for i in range(10):
                response = await client.get(
                    "/api/v1/download/download-pdf",
                    params={"token": token1}
                )
                assert response.status_code == 200

            # User 2: Should still be able to download (independent limit)
            response = await client.get(
                "/api/v1/download/download-pdf",
                params={"token": token2}
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_blob_storage_error_handling(
        self,
        client: AsyncClient,
        db_session,
        sample_meal_plan,
    ):
        """Test error handling when blob storage fails."""
        # Generate magic link token
        token, _ = await generate_magic_link_token(
            email=sample_meal_plan.email,
            ip_address="192.168.1.1",
            db=db_session,
        )

        # Mock blob storage to raise error
        from src.services.blob_storage import BlobStorageError

        with patch("src.api.download.generate_signed_download_url") as mock_signed_url:
            mock_signed_url.side_effect = BlobStorageError(
                "Blob service unavailable",
                error_type="network"
            )

            response = await client.get(
                "/api/v1/download/download-pdf",
                params={"token": token}
            )

            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["code"] == "SERVER_ERROR"
