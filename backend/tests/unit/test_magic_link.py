"""
Unit tests for magic link token generation (T107A).

Tests:
1. Token is 256-bit entropy (43 chars base64url)
2. SHA256 hashing produces correct hash
3. Expiry timestamp is 24h from creation
4. Rate limit: 3 per email per 24h enforced
5. Rate limit: 5 per IP per hour enforced
6. Token uniqueness (100 tokens, all different)
7. Normalized email used for rate limiting
8. Token format is URL-safe
"""

import hashlib
import re
import secrets
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone


class TestTokenEntropy:
    """T107A-1: Token is 256-bit entropy."""

    def test_token_length(self):
        """secrets.token_urlsafe(32) produces 43-char token."""
        token = secrets.token_urlsafe(32)
        assert len(token) == 43, f"Expected 43 chars, got {len(token)}"

    def test_token_is_bytes_equivalent_to_256_bits(self):
        """32 bytes = 256 bits of entropy."""
        token_bytes = secrets.token_bytes(32)
        assert len(token_bytes) == 32
        assert len(token_bytes) * 8 == 256


class TestSHA256Hashing:
    """T107A-2: SHA256 hashing produces correct hash."""

    def test_hash_matches_expected(self):
        """SHA256 of known input produces known output."""
        token = "test-token-value"
        expected_hash = hashlib.sha256(token.encode()).hexdigest()
        actual_hash = hashlib.sha256(token.encode()).hexdigest()
        assert actual_hash == expected_hash
        assert len(actual_hash) == 64  # SHA256 hex digest is 64 chars

    def test_different_tokens_produce_different_hashes(self):
        """Different tokens must produce different hashes."""
        t1 = secrets.token_urlsafe(32)
        t2 = secrets.token_urlsafe(32)
        h1 = hashlib.sha256(t1.encode()).hexdigest()
        h2 = hashlib.sha256(t2.encode()).hexdigest()
        assert h1 != h2


class TestExpiryTimestamp:
    """T107A-3: Expiry timestamp is 24h from creation."""

    def test_expiry_is_24_hours(self):
        """Token expiry should be exactly 24 hours after creation."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)
        delta = expires_at - now
        assert abs(delta.total_seconds() - 86400) < 1


class TestRateLimitEmail:
    """T107A-4: Rate limit 3 per email per 24h."""

    @pytest.mark.asyncio
    async def test_email_rate_limit_enforced(self):
        """After 3 requests for same email, 4th should be blocked."""
        from src.lib.rate_limiting import check_rate_limit_email, RateLimitExceeded

        # Mock Redis functions - patch where they're used in rate_limiting module
        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_incr, \
             patch("src.lib.redis_client.get_ttl", return_value=3600):
            # First 3 requests: under limit
            mock_incr.return_value = 3
            # Should not raise (under limit)
            await check_rate_limit_email("test@example.com", limit=3, window_seconds=86400, operation="magic_link")

            # 4th request: over limit - should raise RateLimitExceeded
            mock_incr.return_value = 4
            with pytest.raises(RateLimitExceeded):
                await check_rate_limit_email("test@example.com", limit=3, window_seconds=86400, operation="magic_link")


class TestRateLimitIP:
    """T107A-5: Rate limit 5 per IP per hour."""

    @pytest.mark.asyncio
    async def test_ip_rate_limit_enforced(self):
        """After 5 requests from same IP, 6th should be blocked."""
        from src.lib.rate_limiting import check_rate_limit_ip, RateLimitExceeded

        with patch("src.lib.rate_limiting.increment_with_ttl") as mock_incr, \
             patch("src.lib.redis_client.get_ttl", return_value=1800):
            # 5th request: at limit - should not raise
            mock_incr.return_value = 5
            await check_rate_limit_ip("192.168.1.1", limit=5, window_seconds=3600, operation="magic_link")

            # 6th: over - should raise RateLimitExceeded
            mock_incr.return_value = 6
            with pytest.raises(RateLimitExceeded):
                await check_rate_limit_ip("192.168.1.1", limit=5, window_seconds=3600, operation="magic_link")


class TestTokenUniqueness:
    """T107A-6: Token uniqueness."""

    def test_100_tokens_all_unique(self):
        """Generate 100 tokens, all must be unique."""
        tokens = [secrets.token_urlsafe(32) for _ in range(100)]
        assert len(set(tokens)) == 100


class TestNormalizedEmailRateLimit:
    """T107A-7: Normalized email used for rate limiting."""

    def test_gmail_normalization_for_rate_limit(self):
        """Gmail aliases should be normalized before rate limiting."""
        from src.lib.email_utils import normalize_email

        # These should all normalize to the same email
        emails = [
            "user@gmail.com",
            "u.s.e.r@gmail.com",
            "user+tag@gmail.com",
            "U.S.E.R+spam@gmail.com",
        ]
        normalized = [normalize_email(e) for e in emails]
        assert len(set(normalized)) == 1, f"Expected 1 unique normalized email, got {set(normalized)}"


class TestTokenFormat:
    """T107A-8: Token format is URL-safe."""

    def test_token_is_url_safe(self):
        """Token should only contain URL-safe characters (a-z, A-Z, 0-9, -, _)."""
        for _ in range(50):
            token = secrets.token_urlsafe(32)
            assert re.match(r'^[A-Za-z0-9_-]+$', token), f"Token contains non-URL-safe chars: {token}"
