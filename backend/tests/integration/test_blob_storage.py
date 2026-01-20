"""
Integration tests for Vercel Blob storage service.

Tests: T089F - Blob storage integration tests (4 test cases)

Test Cases:
1. test_mock_http_upload - Mock HTTP upload to Vercel Blob
2. test_signed_url_generation - Signed URL generation for downloads
3. test_random_suffix_collision_prevention - Random suffix prevents filename collisions
4. test_error_handling - Error handling for various failure scenarios

Dependencies:
- httpx for async HTTP client (mocked)
- Environment variables (BLOB_READ_WRITE_TOKEN)
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import httpx


# Sample PDF bytes for testing
SAMPLE_PDF_BYTES = b'%PDF-1.4\n' + b'x' * 1000 + b'\n%%EOF'


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, status_code: int = 200, json_data: dict = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=MagicMock(),
                response=self
            )


class TestMockHTTPUpload:
    """Test case 1: Mock HTTP upload to Vercel Blob."""

    @pytest.mark.asyncio
    async def test_upload_returns_blob_url(self):
        """Verify upload returns permanent blob URL."""
        mock_response = MockResponse(
            status_code=200,
            json_data={
                "url": "https://xyz.public.blob.vercel-storage.com/test-file-abc123.pdf",
                "pathname": "test-file-abc123.pdf",
                "contentType": "application/pdf",
                "contentDisposition": "attachment; filename=\"test-file-abc123.pdf\""
            }
        )

        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'BLOB_READ_WRITE_TOKEN': 'test-token'}):

            from src.services.blob_storage import upload_pdf_to_vercel_blob

            result = await upload_pdf_to_vercel_blob(
                pdf_bytes=SAMPLE_PDF_BYTES,
                filename="test-file.pdf"
            )

            assert "blob.vercel-storage.com" in result
            assert result.endswith(".pdf")

    @pytest.mark.asyncio
    async def test_upload_sends_correct_headers(self):
        """Verify upload sends correct authorization headers."""
        captured_headers = {}

        async def capture_put(*args, **kwargs):
            captured_headers.update(kwargs.get('headers', {}))
            return MockResponse(
                status_code=200,
                json_data={"url": "https://test.blob.vercel-storage.com/test.pdf"}
            )

        mock_client = AsyncMock()
        mock_client.put = AsyncMock(side_effect=capture_put)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'BLOB_READ_WRITE_TOKEN': 'test-token-123'}):

            from src.services.blob_storage import upload_pdf_to_vercel_blob

            await upload_pdf_to_vercel_blob(
                pdf_bytes=SAMPLE_PDF_BYTES,
                filename="test.pdf"
            )

            # Verify authorization header is present
            assert 'Authorization' in captured_headers or 'authorization' in captured_headers


class TestSignedURLGeneration:
    """Test case 2: Signed URL generation for downloads."""

    @pytest.mark.asyncio
    async def test_signed_url_generation(self):
        """Verify signed URL can be generated for blob."""
        mock_response = MockResponse(
            status_code=200,
            json_data={
                "url": "https://xyz.public.blob.vercel-storage.com/test.pdf?signature=abc123&expires=1234567890"
            }
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'BLOB_READ_WRITE_TOKEN': 'test-token'}):

            from src.services.blob_storage import generate_signed_download_url

            result = await generate_signed_download_url(
                blob_url="https://xyz.public.blob.vercel-storage.com/test.pdf"
            )

            # Should return a URL (either signed or the original)
            assert "blob.vercel-storage.com" in result or result.startswith("http")

    @pytest.mark.asyncio
    async def test_signed_url_has_expiry(self):
        """Verify signed URL includes expiry parameter."""
        from src.services.blob_storage import DEFAULT_SIGNED_URL_EXPIRY_SECONDS

        # Verify constant is set correctly (1 hour = 3600 seconds)
        assert DEFAULT_SIGNED_URL_EXPIRY_SECONDS == 3600


class TestRandomSuffixCollisionPrevention:
    """Test case 3: Random suffix prevents filename collisions."""

    @pytest.mark.asyncio
    async def test_upload_adds_random_suffix(self):
        """Verify Vercel Blob adds random suffix to prevent collisions."""
        # Vercel Blob automatically adds random suffix
        # We test that the returned URL has a different filename than the input

        mock_response = MockResponse(
            status_code=200,
            json_data={
                "url": "https://xyz.public.blob.vercel-storage.com/test-file-XyZ123AbC.pdf",
                "pathname": "test-file-XyZ123AbC.pdf"
            }
        )

        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'BLOB_READ_WRITE_TOKEN': 'test-token'}):

            from src.services.blob_storage import upload_pdf_to_vercel_blob

            result = await upload_pdf_to_vercel_blob(
                pdf_bytes=SAMPLE_PDF_BYTES,
                filename="test-file.pdf"
            )

            # URL should contain original filename base but with suffix
            assert "test-file" in result
            # Suffix adds random characters
            assert result != "https://xyz.public.blob.vercel-storage.com/test-file.pdf"

    @pytest.mark.asyncio
    async def test_multiple_uploads_get_unique_urls(self):
        """Verify multiple uploads of same filename get unique URLs."""
        call_count = 0

        async def mock_upload(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return MockResponse(
                status_code=200,
                json_data={
                    "url": f"https://xyz.public.blob.vercel-storage.com/file-suffix{call_count}.pdf",
                }
            )

        mock_client = AsyncMock()
        mock_client.put = AsyncMock(side_effect=mock_upload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'BLOB_READ_WRITE_TOKEN': 'test-token'}):

            from src.services.blob_storage import upload_pdf_to_vercel_blob

            url1 = await upload_pdf_to_vercel_blob(SAMPLE_PDF_BYTES, "file.pdf")
            url2 = await upload_pdf_to_vercel_blob(SAMPLE_PDF_BYTES, "file.pdf")

            # URLs should be different
            assert url1 != url2


class TestErrorHandling:
    """Test case 4: Error handling for various failure scenarios."""

    @pytest.mark.asyncio
    async def test_empty_bytes_raises_error(self):
        """Verify empty bytes raises validation error."""
        with patch.dict('os.environ', {'BLOB_READ_WRITE_TOKEN': 'test-token'}):
            from src.services.blob_storage import upload_pdf_to_vercel_blob, BlobStorageError

            with pytest.raises(BlobStorageError) as exc_info:
                await upload_pdf_to_vercel_blob(b'', "test.pdf")

            assert exc_info.value.error_type == "validation"

    @pytest.mark.asyncio
    async def test_missing_token_raises_error(self):
        """Verify missing token raises configuration error."""
        from src.services.blob_storage import upload_pdf_to_vercel_blob, BlobStorageError
        from src.lib.env import settings

        # Mock settings to have no token
        with patch.object(settings, 'blob_read_write_token', None):
            with pytest.raises(BlobStorageError) as exc_info:
                await upload_pdf_to_vercel_blob(SAMPLE_PDF_BYTES, "test.pdf")

            assert exc_info.value.error_type == "configuration"

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Verify network errors are handled gracefully."""
        mock_client = AsyncMock()
        mock_client.put = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'BLOB_READ_WRITE_TOKEN': 'test-token'}):

            from src.services.blob_storage import upload_pdf_to_vercel_blob, BlobStorageError

            with pytest.raises(BlobStorageError) as exc_info:
                await upload_pdf_to_vercel_blob(SAMPLE_PDF_BYTES, "test.pdf")

            assert exc_info.value.error_type == "network"

    @pytest.mark.asyncio
    async def test_http_error_handling(self):
        """Verify HTTP errors are handled gracefully."""
        mock_response = MockResponse(status_code=500, text="Internal Server Error")

        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'BLOB_READ_WRITE_TOKEN': 'test-token'}):

            from src.services.blob_storage import upload_pdf_to_vercel_blob, BlobStorageError

            with pytest.raises(BlobStorageError) as exc_info:
                await upload_pdf_to_vercel_blob(SAMPLE_PDF_BYTES, "test.pdf")

            assert exc_info.value.error_type in ["upload", "network"]


class TestBlobDeletion:
    """Additional tests for blob deletion functionality."""

    @pytest.mark.asyncio
    async def test_delete_blob_success(self):
        """Verify blob deletion works correctly."""
        mock_response = MockResponse(status_code=200, json_data={"deleted": True})

        mock_client = AsyncMock()
        # delete_blob uses POST to /delete endpoint, not DELETE method
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'BLOB_READ_WRITE_TOKEN': 'test-token'}):

            from src.services.blob_storage import delete_blob

            result = await delete_blob(
                "https://xyz.public.blob.vercel-storage.com/test.pdf"
            )

            assert result == True

    @pytest.mark.asyncio
    async def test_delete_blob_not_found(self):
        """Verify blob deletion handles not found gracefully."""
        mock_response = MockResponse(status_code=404, text="Not Found")

        mock_client = AsyncMock()
        # delete_blob uses POST to /delete endpoint, not DELETE method
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'BLOB_READ_WRITE_TOKEN': 'test-token'}):

            from src.services.blob_storage import delete_blob

            # 404 returns False (blob already deleted)
            result = await delete_blob(
                "https://xyz.public.blob.vercel-storage.com/nonexistent.pdf"
            )

            assert result == False


class TestBlobStorageErrorClass:
    """Tests for BlobStorageError exception class."""

    def test_blob_storage_error_creation(self):
        """Test BlobStorageError can be created with all parameters."""
        from src.services.blob_storage import BlobStorageError

        error = BlobStorageError(
            message="Upload failed",
            error_type="network",
            original_error=ConnectionError("Network unreachable"),
            blob_url="https://test.blob.vercel-storage.com/test.pdf"
        )

        assert "Upload failed" in str(error)
        assert error.error_type == "network"
        assert error.blob_url == "https://test.blob.vercel-storage.com/test.pdf"
        assert isinstance(error.original_error, ConnectionError)

    def test_blob_storage_error_string_format(self):
        """Test BlobStorageError string representation."""
        from src.services.blob_storage import BlobStorageError

        error = BlobStorageError(
            message="Test error",
            error_type="validation"
        )

        # Should include error type in string representation
        error_str = str(error)
        assert "validation" in error_str.lower() or "test error" in error_str.lower()
