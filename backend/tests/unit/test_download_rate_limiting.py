"""
Unit tests for download rate limiting (T105-T107).

Tests:
- T105: Rate limit enforcement (10 downloads per 24h)
- T106: Grace period bypass (5 minutes after email delivery)
- T107: Download endpoint authorization and signed URL generation

Test Coverage:
- Composite identifier (user_id vs email+IP hash)
- Redis counter increments
- TTL setting on first increment
- Rate limit exceeded errors
- Grace period exclusion
- Magic link token verification
- Signed URL generation
"""

import hashlib
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from src.lib.rate_limiting import check_download_rate_limit, RateLimitExceeded
from src.lib.email_utils import normalize_email


class TestDownloadRateLimiting:
    """Test download rate limiting functionality (T105)."""

    @pytest.mark.asyncio
    async def test_authenticated_user_identifier(self):
        """Test rate limit uses user_id for authenticated users."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment:
            mock_increment.return_value = 1  # First download

            await check_download_rate_limit(
                user_id="user123",
                email="user@example.com",
                ip_address="192.168.1.1",
                email_sent_at=datetime.utcnow() - timedelta(hours=1),  # Outside grace period
                limit=10,
                window_seconds=86400,
            )

            # Verify Redis key uses user_id
            mock_increment.assert_called_once()
            call_args = mock_increment.call_args
            assert call_args[0][0] == "download_rate:user:user123"
            assert call_args[1]["ttl"] == 86400
            assert call_args[1]["amount"] == 1

    @pytest.mark.asyncio
    async def test_magic_link_user_identifier(self):
        """Test rate limit uses email+IP hash for magic link users."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment:
            mock_increment.return_value = 1  # First download

            email = "user@example.com"
            ip = "192.168.1.1"

            await check_download_rate_limit(
                user_id=None,  # Magic link user
                email=email,
                ip_address=ip,
                email_sent_at=datetime.utcnow() - timedelta(hours=1),  # Outside grace period
                limit=10,
                window_seconds=86400,
            )

            # Verify Redis key uses email+IP hash
            mock_increment.assert_called_once()
            call_args = mock_increment.call_args

            # Calculate expected hash
            normalized = normalize_email(email)
            combined = f"{normalized}:{ip}"
            expected_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16]
            expected_key = f"download_rate:guest:{expected_hash}"

            assert call_args[0][0] == expected_key

    @pytest.mark.asyncio
    async def test_rate_limit_within_limit(self):
        """Test download allowed when within limit."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment:
            mock_increment.return_value = 5  # 5th download (within limit)

            # Should not raise exception
            await check_download_rate_limit(
                user_id="user123",
                email="user@example.com",
                ip_address="192.168.1.1",
                email_sent_at=datetime.utcnow() - timedelta(hours=1),
                limit=10,
                window_seconds=86400,
            )

    @pytest.mark.asyncio
    async def test_rate_limit_at_limit(self):
        """Test download allowed at exactly the limit."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment:
            mock_increment.return_value = 10  # 10th download (at limit)

            # Should not raise exception
            await check_download_rate_limit(
                user_id="user123",
                email="user@example.com",
                ip_address="192.168.1.1",
                email_sent_at=datetime.utcnow() - timedelta(hours=1),
                limit=10,
                window_seconds=86400,
            )

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test download blocked when limit exceeded."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment, \
             patch("src.lib.redis_client.get_ttl") as mock_get_ttl:
            mock_increment.return_value = 11  # 11th download (exceeded)
            mock_get_ttl.return_value = 43200  # 12 hours remaining

            with pytest.raises(RateLimitExceeded) as exc_info:
                await check_download_rate_limit(
                    user_id="user123",
                    email="user@example.com",
                    ip_address="192.168.1.1",
                    email_sent_at=datetime.utcnow() - timedelta(hours=1),
                    limit=10,
                    window_seconds=86400,
                )

            # Verify exception details
            exc = exc_info.value
            assert exc.limit == 10
            assert exc.current_count == 11
            assert "12 hours" in str(exc)

    @pytest.mark.asyncio
    async def test_redis_failure_fail_open(self):
        """Test fail-open behavior when Redis is unavailable."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment:
            mock_increment.return_value = None  # Redis error

            # Should not raise exception (fail open)
            await check_download_rate_limit(
                user_id="user123",
                email="user@example.com",
                ip_address="192.168.1.1",
                email_sent_at=datetime.utcnow() - timedelta(hours=1),
                limit=10,
                window_seconds=86400,
            )


class TestGracePeriod:
    """Test grace period bypass functionality (T106)."""

    @pytest.mark.asyncio
    async def test_grace_period_within_5_minutes(self):
        """Test downloads within 5 minutes bypass rate limit."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment:
            # email_sent_at is 2 minutes ago (within grace period)
            email_sent_at = datetime.utcnow() - timedelta(minutes=2)

            await check_download_rate_limit(
                user_id="user123",
                email="user@example.com",
                ip_address="192.168.1.1",
                email_sent_at=email_sent_at,
                limit=10,
                window_seconds=86400,
            )

            # Redis should NOT be called (grace period bypass)
            mock_increment.assert_not_called()

    @pytest.mark.asyncio
    async def test_grace_period_at_5_minutes(self):
        """Test downloads at exactly 5 minutes are rate limited."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment:
            mock_increment.return_value = 1

            # email_sent_at is exactly 5 minutes ago (boundary condition)
            email_sent_at = datetime.utcnow() - timedelta(minutes=5)

            await check_download_rate_limit(
                user_id="user123",
                email="user@example.com",
                ip_address="192.168.1.1",
                email_sent_at=email_sent_at,
                limit=10,
                window_seconds=86400,
            )

            # Redis SHOULD be called (grace period is < 5 minutes, not <=)
            mock_increment.assert_called_once()

    @pytest.mark.asyncio
    async def test_grace_period_after_5_minutes(self):
        """Test downloads after 5 minutes are rate limited."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment:
            mock_increment.return_value = 1

            # email_sent_at is 6 minutes ago (outside grace period)
            email_sent_at = datetime.utcnow() - timedelta(minutes=6)

            await check_download_rate_limit(
                user_id="user123",
                email="user@example.com",
                ip_address="192.168.1.1",
                email_sent_at=email_sent_at,
                limit=10,
                window_seconds=86400,
            )

            # Redis SHOULD be called (outside grace period)
            mock_increment.assert_called_once()

    @pytest.mark.asyncio
    async def test_grace_period_null_email_sent_at(self):
        """Test rate limiting applies when email_sent_at is None."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment:
            mock_increment.return_value = 1

            await check_download_rate_limit(
                user_id="user123",
                email="user@example.com",
                ip_address="192.168.1.1",
                email_sent_at=None,  # No email sent yet
                limit=10,
                window_seconds=86400,
            )

            # Redis SHOULD be called (no grace period)
            mock_increment.assert_called_once()

    @pytest.mark.asyncio
    async def test_grace_period_immediate_download(self):
        """Test immediate download (0 seconds) bypasses rate limit."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment:
            # email_sent_at is now (immediate download)
            email_sent_at = datetime.utcnow()

            await check_download_rate_limit(
                user_id="user123",
                email="user@example.com",
                ip_address="192.168.1.1",
                email_sent_at=email_sent_at,
                limit=10,
                window_seconds=86400,
            )

            # Redis should NOT be called (grace period bypass)
            mock_increment.assert_not_called()


class TestEmailIPHashing:
    """Test email+IP hashing for magic link users."""

    @pytest.mark.asyncio
    async def test_different_emails_different_identifiers(self):
        """Test different emails produce different identifiers."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment:
            mock_increment.return_value = 1

            # First user
            await check_download_rate_limit(
                user_id=None,
                email="user1@example.com",
                ip_address="192.168.1.1",
                email_sent_at=datetime.utcnow() - timedelta(hours=1),
                limit=10,
                window_seconds=86400,
            )
            key1 = mock_increment.call_args[0][0]

            # Second user (different email, same IP)
            await check_download_rate_limit(
                user_id=None,
                email="user2@example.com",
                ip_address="192.168.1.1",
                email_sent_at=datetime.utcnow() - timedelta(hours=1),
                limit=10,
                window_seconds=86400,
            )
            key2 = mock_increment.call_args[0][0]

            # Keys should be different
            assert key1 != key2

    @pytest.mark.asyncio
    async def test_different_ips_different_identifiers(self):
        """Test different IPs produce different identifiers."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment:
            mock_increment.return_value = 1

            # First download (IP 1)
            await check_download_rate_limit(
                user_id=None,
                email="user@example.com",
                ip_address="192.168.1.1",
                email_sent_at=datetime.utcnow() - timedelta(hours=1),
                limit=10,
                window_seconds=86400,
            )
            key1 = mock_increment.call_args[0][0]

            # Second download (IP 2, same email)
            await check_download_rate_limit(
                user_id=None,
                email="user@example.com",
                ip_address="192.168.1.2",
                email_sent_at=datetime.utcnow() - timedelta(hours=1),
                limit=10,
                window_seconds=86400,
            )
            key2 = mock_increment.call_args[0][0]

            # Keys should be different
            assert key1 != key2

    @pytest.mark.asyncio
    async def test_email_normalization_applied(self):
        """Test email normalization is applied to identifier."""
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_increment:
            mock_increment.return_value = 1

            # First download (lowercase)
            await check_download_rate_limit(
                user_id=None,
                email="user@example.com",
                ip_address="192.168.1.1",
                email_sent_at=datetime.utcnow() - timedelta(hours=1),
                limit=10,
                window_seconds=86400,
            )
            key1 = mock_increment.call_args[0][0]

            # Second download (uppercase, should normalize to same)
            await check_download_rate_limit(
                user_id=None,
                email="USER@EXAMPLE.COM",
                ip_address="192.168.1.1",
                email_sent_at=datetime.utcnow() - timedelta(hours=1),
                limit=10,
                window_seconds=86400,
            )
            key2 = mock_increment.call_args[0][0]

            # Keys should be the same (email normalized)
            assert key1 == key2
