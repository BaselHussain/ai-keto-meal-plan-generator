"""
Integration tests for email verification service.

Tests: T089A - Email verification integration tests (8 test cases)

Test Cases:
1. test_generate_verification_code - Code generation produces 6-digit cryptographic code
2. test_code_expiry_10_minutes - Code expires after 10 minutes
3. test_resend_cooldown_60_seconds - 60-second cooldown between resends
4. test_redis_storage - Code stored correctly in Redis
5. test_code_verification_success - Valid code verification succeeds
6. test_code_verification_failure - Invalid code verification fails
7. test_verified_status_24_hours - Verified status persists for 24 hours
8. test_rate_limiting - Rate limiting enforced via cooldown

Dependencies:
- Redis (mocked for unit isolation)
- Email service (mocked)
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import asyncio

# Test constants matching the service
CODE_LENGTH = 6
CODE_EXPIRY_SECONDS = 600  # 10 minutes
VERIFIED_STATUS_SECONDS = 86400  # 24 hours
RESEND_COOLDOWN_SECONDS = 60  # 60 seconds


class MockRedisStorage:
    """Mock Redis storage for testing without actual Redis connection."""

    def __init__(self):
        self.storage = {}
        self.ttls = {}

    async def set_with_ttl(self, key: str, value: str, ttl: int) -> bool:
        """Store value with TTL."""
        self.storage[key] = value
        self.ttls[key] = ttl
        return True

    async def get_value(self, key: str) -> str | None:
        """Get value by key."""
        return self.storage.get(key)

    async def delete_key(self, key: str) -> bool:
        """Delete key."""
        if key in self.storage:
            del self.storage[key]
            if key in self.ttls:
                del self.ttls[key]
            return True
        return False

    async def get_ttl(self, key: str) -> int | None:
        """Get TTL for key."""
        return self.ttls.get(key)

    def clear(self):
        """Clear all storage."""
        self.storage.clear()
        self.ttls.clear()


@pytest.fixture
def mock_redis():
    """Fixture providing mock Redis storage."""
    return MockRedisStorage()


@pytest.fixture
def mock_email_service():
    """Fixture providing mock email service."""
    async def mock_send(*args, **kwargs):
        return {"success": True, "message_id": "test-msg-123", "attempts": 1}
    return mock_send


class TestCodeGeneration:
    """Test case 1: Code generation produces 6-digit cryptographic code."""

    def test_generate_verification_code_length(self):
        """Verify generated code is exactly 6 digits."""
        from src.services.email_verification import generate_verification_code

        code = generate_verification_code()

        assert len(code) == CODE_LENGTH
        assert code.isdigit()

    def test_generate_verification_code_cryptographic_randomness(self):
        """Verify codes are cryptographically random (not predictable)."""
        from src.services.email_verification import generate_verification_code

        # Generate 100 codes and verify no obvious patterns
        codes = [generate_verification_code() for _ in range(100)]

        # All codes should be different (statistically very unlikely to have duplicates)
        # Allow 1-2 duplicates due to birthday paradox with 10^6 space
        unique_codes = set(codes)
        assert len(unique_codes) >= 95  # At least 95% unique

        # All codes should be valid 6-digit numbers
        for code in codes:
            assert len(code) == CODE_LENGTH
            assert code.isdigit()

    def test_generate_verification_code_no_leading_zeros_stripped(self):
        """Verify codes with leading zeros are preserved."""
        from src.services.email_verification import generate_verification_code

        # Generate many codes to increase chance of getting one with leading zero
        codes = [generate_verification_code() for _ in range(1000)]

        # All should maintain 6 characters even if they have leading zeros
        for code in codes:
            assert len(code) == 6


class TestCodeExpiry:
    """Test case 2: Code expires after 10 minutes."""

    @pytest.mark.asyncio
    async def test_code_stored_with_10_minute_ttl(self, mock_redis):
        """Verify code is stored with correct 10-minute TTL."""
        with patch('src.services.email_verification.set_with_ttl', mock_redis.set_with_ttl), \
             patch('src.services.email_verification.get_value', mock_redis.get_value), \
             patch('src.services.email_verification.get_ttl', mock_redis.get_ttl), \
             patch('src.services.email_verification.delete_key', mock_redis.delete_key), \
             patch('src.services.email_verification.send_verification_email',
                   AsyncMock(return_value={"success": True, "message_id": "test-123", "attempts": 1})):

            from src.services.email_verification import send_verification_code

            result = await send_verification_code("test@example.com")

            assert result["success"] == True

            # Check TTL was set to 600 seconds (10 minutes)
            code_key = "verification_code:test@example.com"
            assert code_key in mock_redis.ttls
            assert mock_redis.ttls[code_key] == CODE_EXPIRY_SECONDS


class TestResendCooldown:
    """Test case 3: 60-second cooldown between resends."""

    @pytest.mark.asyncio
    async def test_cooldown_enforced(self, mock_redis):
        """Verify 60-second cooldown is enforced between sends."""
        with patch('src.services.email_verification.set_with_ttl', mock_redis.set_with_ttl), \
             patch('src.services.email_verification.get_value', mock_redis.get_value), \
             patch('src.services.email_verification.get_ttl', mock_redis.get_ttl), \
             patch('src.services.email_verification.delete_key', mock_redis.delete_key), \
             patch('src.services.email_verification.send_verification_email',
                   AsyncMock(return_value={"success": True, "message_id": "test-123", "attempts": 1})):

            from src.services.email_verification import send_verification_code

            # First send should succeed
            result1 = await send_verification_code("cooldown@example.com")
            assert result1["success"] == True

            # Second send within cooldown should fail
            result2 = await send_verification_code("cooldown@example.com")
            assert result2["success"] == False
            assert "cooldown_remaining" in result2 or "wait" in result2.get("error", "").lower()


class TestRedisStorage:
    """Test case 4: Code stored correctly in Redis."""

    @pytest.mark.asyncio
    async def test_code_stored_in_redis(self, mock_redis):
        """Verify code is stored in Redis with correct key format."""
        with patch('src.services.email_verification.set_with_ttl', mock_redis.set_with_ttl), \
             patch('src.services.email_verification.get_value', mock_redis.get_value), \
             patch('src.services.email_verification.get_ttl', mock_redis.get_ttl), \
             patch('src.services.email_verification.delete_key', mock_redis.delete_key), \
             patch('src.services.email_verification.send_verification_email',
                   AsyncMock(return_value={"success": True, "message_id": "test-123", "attempts": 1})):

            from src.services.email_verification import send_verification_code

            await send_verification_code("redis@example.com")

            # Verify key format
            code_key = "verification_code:redis@example.com"
            assert code_key in mock_redis.storage

            # Verify value is a 6-digit code
            stored_code = mock_redis.storage[code_key]
            assert len(stored_code) == 6
            assert stored_code.isdigit()


class TestCodeVerificationSuccess:
    """Test case 5: Valid code verification succeeds."""

    @pytest.mark.asyncio
    async def test_valid_code_verification(self, mock_redis):
        """Verify correct code passes verification."""
        # Pre-store a code
        mock_redis.storage["verification_code:verify@example.com"] = "123456"
        mock_redis.ttls["verification_code:verify@example.com"] = 600

        with patch('src.services.email_verification.set_with_ttl', mock_redis.set_with_ttl), \
             patch('src.services.email_verification.get_value', mock_redis.get_value), \
             patch('src.services.email_verification.get_ttl', mock_redis.get_ttl), \
             patch('src.services.email_verification.delete_key', mock_redis.delete_key):

            from src.services.email_verification import verify_code

            result = await verify_code("verify@example.com", "123456")

            assert result["success"] == True
            assert "verified" in result.get("message", "").lower() or result["success"]


class TestCodeVerificationFailure:
    """Test case 6: Invalid code verification fails."""

    @pytest.mark.asyncio
    async def test_invalid_code_verification(self, mock_redis):
        """Verify incorrect code fails verification."""
        # Pre-store a code
        mock_redis.storage["verification_code:invalid@example.com"] = "123456"
        mock_redis.ttls["verification_code:invalid@example.com"] = 600

        with patch('src.services.email_verification.set_with_ttl', mock_redis.set_with_ttl), \
             patch('src.services.email_verification.get_value', mock_redis.get_value), \
             patch('src.services.email_verification.get_ttl', mock_redis.get_ttl), \
             patch('src.services.email_verification.delete_key', mock_redis.delete_key):

            from src.services.email_verification import verify_code

            result = await verify_code("invalid@example.com", "999999")  # Wrong code

            assert result["success"] == False
            assert "invalid" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_expired_code_verification(self, mock_redis):
        """Verify expired code fails verification."""
        # No code stored (simulating expiry)

        with patch('src.services.email_verification.set_with_ttl', mock_redis.set_with_ttl), \
             patch('src.services.email_verification.get_value', mock_redis.get_value), \
             patch('src.services.email_verification.get_ttl', mock_redis.get_ttl), \
             patch('src.services.email_verification.delete_key', mock_redis.delete_key):

            from src.services.email_verification import verify_code

            result = await verify_code("expired@example.com", "123456")

            assert result["success"] == False
            assert "expired" in result.get("error", "").lower() or "not found" in result.get("error", "").lower()


class TestVerifiedStatus24Hours:
    """Test case 7: Verified status persists for 24 hours."""

    @pytest.mark.asyncio
    async def test_verified_status_stored_with_24h_ttl(self, mock_redis):
        """Verify verification sets 24-hour status."""
        # Pre-store a code
        mock_redis.storage["verification_code:status@example.com"] = "123456"
        mock_redis.ttls["verification_code:status@example.com"] = 600

        with patch('src.services.email_verification.set_with_ttl', mock_redis.set_with_ttl), \
             patch('src.services.email_verification.get_value', mock_redis.get_value), \
             patch('src.services.email_verification.get_ttl', mock_redis.get_ttl), \
             patch('src.services.email_verification.delete_key', mock_redis.delete_key):

            from src.services.email_verification import verify_code

            result = await verify_code("status@example.com", "123456")

            assert result["success"] == True

            # Check verified status TTL
            verified_key = "verification_verified:status@example.com"
            assert verified_key in mock_redis.ttls
            assert mock_redis.ttls[verified_key] == VERIFIED_STATUS_SECONDS

    @pytest.mark.asyncio
    async def test_is_email_verified_returns_true(self, mock_redis):
        """Verify is_email_verified returns True for verified email."""
        # Pre-store verified status
        mock_redis.storage["verification_verified:verified@example.com"] = datetime.utcnow().isoformat()
        mock_redis.ttls["verification_verified:verified@example.com"] = 86400

        with patch('src.services.email_verification.get_value', mock_redis.get_value), \
             patch('src.services.email_verification.get_ttl', mock_redis.get_ttl):

            from src.services.email_verification import is_email_verified

            result = await is_email_verified("verified@example.com")

            assert result == True


class TestRateLimiting:
    """Test case 8: Rate limiting enforced via cooldown."""

    @pytest.mark.asyncio
    async def test_multiple_rapid_requests_blocked(self, mock_redis):
        """Verify multiple rapid requests are blocked by cooldown."""
        with patch('src.services.email_verification.set_with_ttl', mock_redis.set_with_ttl), \
             patch('src.services.email_verification.get_value', mock_redis.get_value), \
             patch('src.services.email_verification.get_ttl', mock_redis.get_ttl), \
             patch('src.services.email_verification.delete_key', mock_redis.delete_key), \
             patch('src.services.email_verification.send_verification_email',
                   AsyncMock(return_value={"success": True, "message_id": "test-123", "attempts": 1})):

            from src.services.email_verification import send_verification_code

            # First request succeeds
            result1 = await send_verification_code("rate@example.com")
            assert result1["success"] == True

            # Rapid subsequent requests should fail
            for i in range(3):
                result = await send_verification_code("rate@example.com")
                assert result["success"] == False
                # Should mention cooldown/wait
                assert "cooldown_remaining" in result or "wait" in result.get("error", "").lower()
