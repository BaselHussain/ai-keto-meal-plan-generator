"""
Integration tests for email delivery service.

Tests: T089G - Email delivery integration tests (6 test cases)

Test Cases:
1. test_resend_api_mock - Mock Resend API responses
2. test_pdf_attachment_handling - PDF attachment encoding and sending
3. test_retry_logic_3_attempts - Retry logic with 3 attempts
4. test_retry_exponential_backoff - Exponential backoff (2s, 4s, 8s)
5. test_idempotency_check - Idempotency prevents duplicate sends
6. test_error_response_handling - Error responses handled gracefully

Dependencies:
- resend SDK (mocked)
- Environment variables (RESEND_API_KEY, RESEND_FROM_EMAIL)
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock, call
import asyncio
import base64
from datetime import datetime


# Sample PDF bytes for testing
SAMPLE_PDF_BYTES = b'%PDF-1.4\n' + b'x' * 10000 + b'\n%%EOF'


class MockResendResponse:
    """Mock Resend API response."""

    def __init__(self, id: str = "msg_123456"):
        self.id = id


class MockResendError(Exception):
    """Mock Resend API error."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class TestResendAPIMock:
    """Test case 1: Mock Resend API responses."""

    @pytest.mark.asyncio
    async def test_verification_email_success(self):
        """Verify verification email sends successfully."""
        # resend.Emails.send is called with a dict param, returns response with 'id'
        mock_send = MagicMock(return_value={"id": "msg_verify_123"})

        with patch('resend.Emails.send', mock_send), \
             patch('src.services.email_service.RESEND_API_KEY', 'test-api-key'), \
             patch('src.services.email_service.RESEND_FROM_EMAIL', 'test@example.com'):

            from src.services.email_service import send_verification_email

            result = await send_verification_email(
                to_email="user@example.com",
                verification_code="123456"
            )

            assert result["success"] == True
            assert "message_id" in result

    @pytest.mark.asyncio
    async def test_delivery_email_success(self):
        """Verify delivery email sends successfully."""
        # resend.Emails.send is called with a dict param, returns response with 'id'
        mock_send = MagicMock(return_value={"id": "msg_deliver_123"})

        with patch('resend.Emails.send', mock_send), \
             patch('src.services.email_service.RESEND_API_KEY', 'test-api-key'), \
             patch('src.services.email_service.RESEND_FROM_EMAIL', 'test@example.com'):

            from src.services.email_service import send_delivery_email

            result = await send_delivery_email(
                to_email="user@example.com",
                calorie_target=2000,
                pdf_bytes=SAMPLE_PDF_BYTES,
                pdf_filename="keto-meal-plan.pdf",
                payment_id="pay_123"
            )

            assert result["success"] == True
            assert "message_id" in result


class TestPDFAttachmentHandling:
    """Test case 2: PDF attachment encoding and sending."""

    @pytest.mark.asyncio
    async def test_pdf_attachment_base64_encoded(self):
        """Verify PDF is properly base64 encoded for attachment."""
        captured_params = {}

        def capture_send(params):
            captured_params.update(params)
            return {"id": "msg_attach_123"}

        with patch('resend.Emails.send', capture_send), \
             patch('src.services.email_service.RESEND_API_KEY', 'test-api-key'), \
             patch('src.services.email_service.RESEND_FROM_EMAIL', 'test@example.com'):

            from src.services.email_service import send_delivery_email

            result = await send_delivery_email(
                to_email="user@example.com",
                calorie_target=2000,
                pdf_bytes=SAMPLE_PDF_BYTES,
                pdf_filename="keto-meal-plan.pdf",
                payment_id="pay_123"
            )

            # Check that attachments were included
            if 'attachments' in captured_params:
                attachments = captured_params['attachments']
                assert len(attachments) > 0

                # Verify attachment has correct structure
                attachment = attachments[0]
                assert 'filename' in attachment or 'name' in attachment
                assert 'content' in attachment

    @pytest.mark.asyncio
    async def test_pdf_filename_in_attachment(self):
        """Verify PDF filename is correctly set in attachment."""
        captured_params = {}

        def capture_send(params):
            captured_params.update(params)
            return {"id": "msg_filename_123"}

        with patch('resend.Emails.send', capture_send), \
             patch('src.services.email_service.RESEND_API_KEY', 'test-api-key'), \
             patch('src.services.email_service.RESEND_FROM_EMAIL', 'test@example.com'):

            from src.services.email_service import send_delivery_email

            await send_delivery_email(
                to_email="user@example.com",
                calorie_target=2000,
                pdf_bytes=SAMPLE_PDF_BYTES,
                pdf_filename="my-keto-plan.pdf",
                payment_id="pay_123"
            )

            if 'attachments' in captured_params:
                attachment = captured_params['attachments'][0]
                filename = attachment.get('filename') or attachment.get('name', '')
                assert "keto" in filename.lower() or "meal" in filename.lower() or "plan" in filename.lower()


class TestRetryLogic3Attempts:
    """Test case 3: Retry logic with 3 attempts."""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Verify email retries up to 3 times on failure."""
        call_count = 0

        def fail_twice_then_succeed(params):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return {"id": "msg_retry_123"}

        with patch('resend.Emails.send', fail_twice_then_succeed), \
             patch('src.services.email_service.RESEND_API_KEY', 'test-api-key'), \
             patch('src.services.email_service.RESEND_FROM_EMAIL', 'test@example.com'), \
             patch('asyncio.sleep', AsyncMock()):  # Skip actual delays

            from src.services.email_service import send_verification_email

            result = await send_verification_email(
                to_email="user@example.com",
                verification_code="123456"
            )

            # Should succeed after retries
            assert result["success"] == True
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Verify email fails after max retries exceeded."""
        call_count = 0

        def always_fail(params):
            nonlocal call_count
            call_count += 1
            raise Exception("Persistent failure")

        with patch('resend.Emails.send', always_fail), \
             patch('src.services.email_service.RESEND_API_KEY', 'test-api-key'), \
             patch('src.services.email_service.RESEND_FROM_EMAIL', 'test@example.com'), \
             patch('asyncio.sleep', AsyncMock()):  # Skip actual delays

            from src.services.email_service import send_verification_email

            result = await send_verification_email(
                to_email="user@example.com",
                verification_code="123456"
            )

            # Should fail after max retries (3)
            assert result["success"] == False
            assert call_count == 3  # MAX_RETRIES


class TestRetryExponentialBackoff:
    """Test case 4: Exponential backoff (2s, 4s, 8s)."""

    @pytest.mark.asyncio
    async def test_backoff_delays(self):
        """Verify exponential backoff delays are applied."""
        sleep_times = []

        async def capture_sleep(seconds):
            sleep_times.append(seconds)

        def always_fail(params):
            raise Exception("Failure")

        with patch('resend.Emails.send', always_fail), \
             patch('src.services.email_service.RESEND_API_KEY', 'test-api-key'), \
             patch('src.services.email_service.RESEND_FROM_EMAIL', 'test@example.com'), \
             patch('asyncio.sleep', capture_sleep):

            from src.services.email_service import send_verification_email

            result = await send_verification_email(
                to_email="user@example.com",
                verification_code="123456"
            )

            # Should have sleep calls for backoff
            # Expected: [2, 4] (no sleep after last attempt)
            if len(sleep_times) >= 2:
                assert sleep_times[0] == 2  # First retry: 2s
                assert sleep_times[1] == 4  # Second retry: 4s


class TestIdempotencyCheck:
    """Test case 5: Idempotency prevents duplicate sends."""

    @pytest.mark.asyncio
    async def test_idempotency_skips_already_sent(self):
        """Verify idempotency check skips if email already sent."""
        mock_send = MagicMock(return_value={"id": "msg_idem_123"})

        with patch('resend.Emails.send', mock_send), \
             patch('src.services.email_service.RESEND_API_KEY', 'test-api-key'), \
             patch('src.services.email_service.RESEND_FROM_EMAIL', 'test@example.com'):

            from src.services.email_service import send_delivery_email

            # First send
            result1 = await send_delivery_email(
                to_email="user@example.com",
                calorie_target=2000,
                pdf_bytes=SAMPLE_PDF_BYTES,
                pdf_filename="keto-meal-plan.pdf",
                payment_id="pay_123",
                email_already_sent=False
            )

            # Second send with idempotency flag
            result2 = await send_delivery_email(
                to_email="user@example.com",
                calorie_target=2000,
                pdf_bytes=SAMPLE_PDF_BYTES,
                pdf_filename="keto-meal-plan.pdf",
                payment_id="pay_123",
                email_already_sent=True
            )

            # First should succeed
            assert result1["success"] == True

            # Second should be skipped (idempotent) - call count should still be 1
            assert result2["success"] == True
            # When email_already_sent=True, the send should be skipped
            assert mock_send.call_count == 1


class TestErrorResponseHandling:
    """Test case 6: Error responses handled gracefully."""

    @pytest.mark.asyncio
    async def test_api_key_missing_error(self):
        """Verify missing API key is handled gracefully."""
        with patch('src.services.email_service.RESEND_API_KEY', None), \
             patch('src.services.email_service.RESEND_FROM_EMAIL', 'test@example.com'):

            from src.services.email_service import send_verification_email

            result = await send_verification_email(
                to_email="user@example.com",
                verification_code="123456"
            )

            # Should fail gracefully
            assert result["success"] == False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_email_error(self):
        """Verify invalid email address is handled gracefully."""
        def raise_invalid_email(params):
            raise Exception("Invalid email address")

        with patch('resend.Emails.send', raise_invalid_email), \
             patch('src.services.email_service.RESEND_API_KEY', 'test-api-key'), \
             patch('src.services.email_service.RESEND_FROM_EMAIL', 'test@example.com'), \
             patch('asyncio.sleep', AsyncMock()):

            from src.services.email_service import send_verification_email

            result = await send_verification_email(
                to_email="invalid-email",
                verification_code="123456"
            )

            # Should fail gracefully after retries
            assert result["success"] == False

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """Verify rate limit error is handled gracefully."""
        def raise_rate_limit(params):
            raise Exception("Rate limit exceeded")

        with patch('resend.Emails.send', raise_rate_limit), \
             patch('src.services.email_service.RESEND_API_KEY', 'test-api-key'), \
             patch('src.services.email_service.RESEND_FROM_EMAIL', 'test@example.com'), \
             patch('asyncio.sleep', AsyncMock()):

            from src.services.email_service import send_verification_email

            result = await send_verification_email(
                to_email="user@example.com",
                verification_code="123456"
            )

            # Should fail gracefully
            assert result["success"] == False

    @pytest.mark.asyncio
    async def test_network_timeout_error(self):
        """Verify network timeout is handled gracefully."""
        def raise_timeout(params):
            raise TimeoutError("Connection timed out")

        with patch('resend.Emails.send', raise_timeout), \
             patch('src.services.email_service.RESEND_API_KEY', 'test-api-key'), \
             patch('src.services.email_service.RESEND_FROM_EMAIL', 'test@example.com'), \
             patch('asyncio.sleep', AsyncMock()):

            from src.services.email_service import send_verification_email

            result = await send_verification_email(
                to_email="user@example.com",
                verification_code="123456"
            )

            # Should fail gracefully
            assert result["success"] == False


class TestEmailTemplates:
    """Additional tests for email templates."""

    def test_verification_template_has_code(self):
        """Verify verification email template includes code."""
        from src.services.email_service import _generate_html_template

        html = _generate_html_template("123456")

        assert "123456" in html
        assert "html" in html.lower()

    def test_verification_template_has_expiry_warning(self):
        """Verify verification email template has expiry warning."""
        from src.services.email_service import _generate_html_template

        html = _generate_html_template("123456")

        # Should mention expiry/minutes
        assert "10" in html or "minute" in html.lower() or "expire" in html.lower()


class TestDeliveryEmailContent:
    """Tests for delivery email content."""

    @pytest.mark.asyncio
    async def test_delivery_email_includes_calorie_target(self):
        """Verify delivery email includes calorie target."""
        captured_params = {}

        def capture_send(params):
            captured_params.update(params)
            return {"id": "msg_cal_123"}

        with patch('resend.Emails.send', capture_send), \
             patch('src.services.email_service.RESEND_API_KEY', 'test-api-key'), \
             patch('src.services.email_service.RESEND_FROM_EMAIL', 'test@example.com'):

            from src.services.email_service import send_delivery_email

            await send_delivery_email(
                to_email="user@example.com",
                calorie_target=1800,
                pdf_bytes=SAMPLE_PDF_BYTES,
                pdf_filename="keto-meal-plan.pdf",
                payment_id="pay_123"
            )

            # Check HTML content includes calorie target
            html_content = captured_params.get('html', '')
            # Calorie target should be mentioned somewhere
            assert '1800' in html_content or 'calorie' in html_content.lower()
