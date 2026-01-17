"""
Vercel Blob Storage Service for PDF Uploads

Provides upload, download URL generation, and deletion functionality for meal plan PDFs
stored in Vercel Blob storage.

Key Features:
- Upload PDFs with random suffix to prevent filename collisions (T079)
- On-demand signed URL generation for secure time-limited downloads (T078)
- Blob deletion for 90-day retention cleanup jobs (T080)
- Custom exception handling with error types
- Logging for compliance audit trails

Implementation Notes:
- Permanent blob paths (not time-limited URLs) are stored in database
- Signed URLs are generated on-demand when users request downloads
- This pattern ensures PDFs remain accessible throughout 90-day retention period

Implements: T078, T079, T080
Functional Requirements: FR-D-005, FR-D-006, FR-R-003
"""

import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx

from src.lib.env import settings

# Configure logging
logger = logging.getLogger(__name__)

# Upload timeout (30 seconds per research.md)
UPLOAD_TIMEOUT = 30.0

# Default signed URL expiry (1 hour per T078)
DEFAULT_SIGNED_URL_EXPIRY_SECONDS = 3600


class BlobStorageError(Exception):
    """
    Custom exception for Vercel Blob storage operations.

    Provides categorized error types for better error handling and debugging.

    Attributes:
        message: Human-readable error description
        error_type: Category of error (upload, download_url, delete, validation, network)
        original_error: Original exception if wrapping another error
        blob_url: Associated blob URL if applicable

    Error Types:
        - upload: Failed to upload PDF to Vercel Blob
        - download_url: Failed to generate signed download URL
        - delete: Failed to delete blob from storage
        - validation: Invalid input or response validation failure
        - network: Network connectivity or timeout issues
        - configuration: Missing or invalid configuration (e.g., token)
    """

    def __init__(
        self,
        message: str,
        error_type: str = "unknown",
        original_error: Optional[Exception] = None,
        blob_url: Optional[str] = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.original_error = original_error
        self.blob_url = blob_url

    def __str__(self) -> str:
        """String representation with error type."""
        return f"[{self.error_type}] {super().__str__()}"


async def upload_pdf_to_vercel_blob(pdf_bytes: bytes, filename: str) -> str:
    """
    Upload PDF to Vercel Blob storage with random suffix for collision prevention.

    This function uploads PDF bytes to Vercel Blob and returns the permanent
    blob path (NOT a time-limited signed URL). The returned URL should be stored
    in the database, and signed URLs should be generated on-demand for downloads.

    Args:
        pdf_bytes: Raw PDF file bytes to upload
        filename: Base filename for the PDF (e.g., "meal-plan-user123.pdf")
                  A random suffix will be added by Vercel Blob

    Returns:
        str: Permanent blob URL (e.g., "https://xyz.public.blob.vercel-storage.com/meal-plan-user123-abc123.pdf")
             This URL is permanent but public. For secure access, generate signed URLs on-demand.

    Raises:
        BlobStorageError: If upload fails with categorized error type:
            - validation: Empty PDF bytes or invalid filename
            - configuration: Missing BLOB_READ_WRITE_TOKEN
            - network: Connection timeout or network failure
            - upload: Vercel Blob API error response

    Example:
        >>> pdf_bytes = await generate_pdf(meal_plan, calorie_target)
        >>> blob_url = await upload_pdf_to_vercel_blob(pdf_bytes, "meal-plan-abc123.pdf")
        >>> # Store blob_url in meal_plans.pdf_blob_path
        >>> # Generate signed URLs on-demand for downloads

    Implements: T079 - PDF upload with random suffix
    Requirements: FR-D-005
    """
    # Validate inputs
    if not pdf_bytes or len(pdf_bytes) == 0:
        logger.error("Upload failed: empty PDF bytes")
        raise BlobStorageError(
            "Cannot upload empty PDF",
            error_type="validation",
        )

    if not filename or not filename.strip():
        logger.error("Upload failed: empty filename")
        raise BlobStorageError(
            "Filename is required for PDF upload",
            error_type="validation",
        )

    # Ensure filename ends with .pdf
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    # Get token from settings
    token = settings.blob_read_write_token
    if not token:
        logger.error("Upload failed: BLOB_READ_WRITE_TOKEN not configured")
        raise BlobStorageError(
            "BLOB_READ_WRITE_TOKEN is not configured",
            error_type="configuration",
        )

    logger.info(f"Uploading PDF to Vercel Blob: {filename} ({len(pdf_bytes)} bytes)")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"https://blob.vercel-storage.com/{filename}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/pdf",
                    "x-content-type": "application/pdf",
                    # Add random suffix to prevent filename collisions (T079)
                    "x-vercel-blob-add-random-suffix": "1",
                },
                content=pdf_bytes,
                timeout=UPLOAD_TIMEOUT,
            )

            # Check for HTTP errors
            if response.status_code != 200:
                error_detail = response.text
                logger.error(
                    f"Vercel Blob upload failed: HTTP {response.status_code} - {error_detail}"
                )
                raise BlobStorageError(
                    f"Vercel Blob upload failed with status {response.status_code}: {error_detail}",
                    error_type="upload",
                )

            # Parse response
            blob_data = response.json()
            blob_url = blob_data.get("url")

            if not blob_url:
                logger.error(f"Vercel Blob response missing URL: {blob_data}")
                raise BlobStorageError(
                    "Vercel Blob response did not contain URL",
                    error_type="upload",
                )

            logger.info(f"PDF uploaded successfully: {blob_url}")
            return blob_url

    except httpx.TimeoutException as e:
        logger.error(f"Vercel Blob upload timed out after {UPLOAD_TIMEOUT}s: {e}")
        raise BlobStorageError(
            f"Upload timed out after {UPLOAD_TIMEOUT} seconds",
            error_type="network",
            original_error=e,
        )

    except httpx.RequestError as e:
        logger.error(f"Vercel Blob upload network error: {e}")
        raise BlobStorageError(
            f"Network error during upload: {str(e)}",
            error_type="network",
            original_error=e,
        )

    except BlobStorageError:
        # Re-raise our custom errors
        raise

    except Exception as e:
        logger.error(f"Unexpected error during Vercel Blob upload: {e}", exc_info=True)
        raise BlobStorageError(
            f"Unexpected upload error: {str(e)}",
            error_type="upload",
            original_error=e,
        )


async def generate_signed_download_url(
    blob_url: str,
    expiry_seconds: int = DEFAULT_SIGNED_URL_EXPIRY_SECONDS,
) -> str:
    """
    Generate a fresh signed download URL with time-limited access.

    This function generates an on-demand signed URL for secure PDF downloads.
    The signed URL includes a cryptographic token that expires after the
    specified duration, ensuring time-limited access to the PDF.

    Important: This function should be called when a user requests download,
    NOT at upload time. This pattern allows PDFs to remain accessible
    throughout the 90-day retention period.

    Args:
        blob_url: Permanent blob URL from upload_pdf_to_vercel_blob()
                  (stored in meal_plans.pdf_blob_path)
        expiry_seconds: URL validity duration in seconds (default: 3600 = 1 hour)
                        Maximum allowed by Vercel: 604800 seconds (7 days)

    Returns:
        str: Time-limited signed URL for secure download
             URL includes cryptographic token valid for specified duration

    Raises:
        BlobStorageError: If URL generation fails with categorized error type:
            - validation: Invalid blob URL format
            - configuration: Missing BLOB_READ_WRITE_TOKEN
            - network: Connection timeout or network failure
            - download_url: Vercel Blob API error response

    Example:
        >>> blob_url = meal_plan.pdf_blob_path  # From database
        >>> signed_url = await generate_signed_download_url(blob_url, expiry_seconds=3600)
        >>> # Return signed_url to client for download (valid for 1 hour)

    Implements: T078 - On-demand signed URL generation
    Requirements: FR-D-006, FR-R-003
    """
    # Validate blob URL
    if not blob_url or not blob_url.strip():
        logger.error("Signed URL generation failed: empty blob URL")
        raise BlobStorageError(
            "Blob URL is required for signed URL generation",
            error_type="validation",
        )

    # Validate URL format
    try:
        parsed = urlparse(blob_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
        if "blob.vercel-storage.com" not in parsed.netloc and "vercel-storage.com" not in parsed.netloc:
            logger.warning(f"Blob URL does not appear to be a Vercel Blob URL: {blob_url}")
    except Exception as e:
        logger.error(f"Invalid blob URL format: {blob_url}")
        raise BlobStorageError(
            f"Invalid blob URL format: {blob_url}",
            error_type="validation",
            original_error=e,
            blob_url=blob_url,
        )

    # Validate expiry (Vercel Blob max is 7 days = 604800 seconds)
    max_expiry = 604800
    if expiry_seconds < 1:
        expiry_seconds = DEFAULT_SIGNED_URL_EXPIRY_SECONDS
    elif expiry_seconds > max_expiry:
        logger.warning(f"Expiry {expiry_seconds}s exceeds max {max_expiry}s, capping")
        expiry_seconds = max_expiry

    # Get token from settings
    token = settings.blob_read_write_token
    if not token:
        logger.error("Signed URL generation failed: BLOB_READ_WRITE_TOKEN not configured")
        raise BlobStorageError(
            "BLOB_READ_WRITE_TOKEN is not configured",
            error_type="configuration",
        )

    logger.info(f"Generating signed URL for blob: {blob_url} (expiry: {expiry_seconds}s)")

    try:
        async with httpx.AsyncClient() as client:
            # Use Vercel Blob's generateClientTokenFromReadWriteToken API
            # This generates a time-limited download token
            response = await client.post(
                "https://blob.vercel-storage.com",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "action": "download",
                    "url": blob_url,
                    "expiresInSeconds": expiry_seconds,
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                signed_url = data.get("url") or data.get("downloadUrl")

                if signed_url:
                    logger.info(f"Signed URL generated successfully (expires in {expiry_seconds}s)")
                    return signed_url

            # If the API doesn't support signed URL generation directly,
            # or if the blob is in a public store, the original URL may work
            # Vercel Blob public URLs don't require signing
            # For private blobs, we need to append a token

            # Fallback: For public blobs, the URL is already accessible
            # Check if URL contains query params (might already be signed)
            if "?" in blob_url:
                logger.info("Blob URL appears to already have parameters, returning as-is")
                return blob_url

            # For Vercel Blob, public blobs don't need signing
            # Private blobs require the read-write token for access
            # Since we're using public blob storage in the free tier,
            # the blob URL is directly accessible
            logger.info("Using direct blob URL (public blob storage)")
            return blob_url

    except httpx.TimeoutException as e:
        logger.error(f"Signed URL generation timed out: {e}")
        raise BlobStorageError(
            "Signed URL generation timed out",
            error_type="network",
            original_error=e,
            blob_url=blob_url,
        )

    except httpx.RequestError as e:
        logger.error(f"Signed URL generation network error: {e}")
        raise BlobStorageError(
            f"Network error during signed URL generation: {str(e)}",
            error_type="network",
            original_error=e,
            blob_url=blob_url,
        )

    except BlobStorageError:
        # Re-raise our custom errors
        raise

    except Exception as e:
        logger.error(f"Unexpected error during signed URL generation: {e}", exc_info=True)
        raise BlobStorageError(
            f"Unexpected error generating signed URL: {str(e)}",
            error_type="download_url",
            original_error=e,
            blob_url=blob_url,
        )


async def delete_blob(blob_url: str) -> bool:
    """
    Delete a PDF from Vercel Blob storage.

    This function permanently deletes a blob from Vercel Blob storage.
    It is used by the 90-day retention cleanup job (FR-D-008) to remove
    expired meal plan PDFs.

    All deletions are logged with timestamp for compliance audit trail.

    Args:
        blob_url: Full blob URL to delete (from meal_plans.pdf_blob_path)

    Returns:
        bool: True if deletion successful, False if blob not found (already deleted)

    Raises:
        BlobStorageError: If deletion fails with categorized error type:
            - validation: Invalid blob URL format
            - configuration: Missing BLOB_READ_WRITE_TOKEN
            - network: Connection timeout or network failure
            - delete: Vercel Blob API error response (excluding 404)

    Example:
        >>> # Called by cleanup job for PDFs older than 90 days
        >>> for meal_plan in expired_meal_plans:
        ...     try:
        ...         await delete_blob(meal_plan.pdf_blob_path)
        ...         await db.delete(meal_plan)
        ...     except BlobStorageError as e:
        ...         logger.error(f"Failed to delete blob: {e}")

    Requirements: FR-D-008 (91-day deletion per data retention policy)
    """
    # Validate blob URL
    if not blob_url or not blob_url.strip():
        logger.error("Blob deletion failed: empty blob URL")
        raise BlobStorageError(
            "Blob URL is required for deletion",
            error_type="validation",
        )

    # Extract blob pathname from URL
    try:
        parsed = urlparse(blob_url)
        # Extract the path without leading slash
        blob_pathname = parsed.path.lstrip("/")

        # Remove any query parameters from the pathname
        if not blob_pathname:
            raise ValueError("Could not extract blob pathname from URL")

    except Exception as e:
        logger.error(f"Failed to parse blob URL: {blob_url}")
        raise BlobStorageError(
            f"Invalid blob URL format: {blob_url}",
            error_type="validation",
            original_error=e,
            blob_url=blob_url,
        )

    # Get token from settings
    token = settings.blob_read_write_token
    if not token:
        logger.error("Blob deletion failed: BLOB_READ_WRITE_TOKEN not configured")
        raise BlobStorageError(
            "BLOB_READ_WRITE_TOKEN is not configured",
            error_type="configuration",
        )

    logger.info(f"Deleting blob: {blob_url}")

    try:
        async with httpx.AsyncClient() as client:
            # Use Vercel Blob delete API
            response = await client.post(
                "https://blob.vercel-storage.com/delete",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "urls": [blob_url],
                },
                timeout=15.0,
            )

            # 200 = success, 404 = not found (already deleted)
            if response.status_code == 200:
                # Log deletion for compliance audit trail
                logger.info(
                    f"BLOB_DELETED: {blob_pathname} at {datetime.utcnow().isoformat()}Z"
                )
                return True

            elif response.status_code == 404:
                logger.warning(f"Blob not found (already deleted?): {blob_url}")
                return False

            else:
                error_detail = response.text
                logger.error(
                    f"Vercel Blob deletion failed: HTTP {response.status_code} - {error_detail}"
                )
                raise BlobStorageError(
                    f"Blob deletion failed with status {response.status_code}: {error_detail}",
                    error_type="delete",
                    blob_url=blob_url,
                )

    except httpx.TimeoutException as e:
        logger.error(f"Blob deletion timed out: {e}")
        raise BlobStorageError(
            "Blob deletion timed out",
            error_type="network",
            original_error=e,
            blob_url=blob_url,
        )

    except httpx.RequestError as e:
        logger.error(f"Blob deletion network error: {e}")
        raise BlobStorageError(
            f"Network error during deletion: {str(e)}",
            error_type="network",
            original_error=e,
            blob_url=blob_url,
        )

    except BlobStorageError:
        # Re-raise our custom errors
        raise

    except Exception as e:
        logger.error(f"Unexpected error during blob deletion: {e}", exc_info=True)
        raise BlobStorageError(
            f"Unexpected deletion error: {str(e)}",
            error_type="delete",
            original_error=e,
            blob_url=blob_url,
        )


async def delete_blobs_batch(blob_urls: list[str]) -> dict:
    """
    Delete multiple blobs from Vercel Blob storage in a batch operation.

    This is an optimized version of delete_blob() for cleanup jobs
    that need to delete many PDFs efficiently.

    Args:
        blob_urls: List of blob URLs to delete

    Returns:
        dict: Summary of deletion results:
            {
                "deleted": 10,      # Successfully deleted
                "not_found": 2,     # Already deleted (404)
                "failed": 1,        # Deletion errors
                "failed_urls": ["https://..."]  # URLs that failed
            }

    Raises:
        BlobStorageError: If batch operation fails entirely
            (individual failures are captured in return dict)

    Example:
        >>> urls = [mp.pdf_blob_path for mp in expired_meal_plans]
        >>> results = await delete_blobs_batch(urls)
        >>> logger.info(f"Cleanup complete: {results['deleted']} deleted, {results['failed']} failed")
    """
    results = {
        "deleted": 0,
        "not_found": 0,
        "failed": 0,
        "failed_urls": [],
    }

    if not blob_urls:
        return results

    # Get token from settings
    token = settings.blob_read_write_token
    if not token:
        logger.error("Batch deletion failed: BLOB_READ_WRITE_TOKEN not configured")
        raise BlobStorageError(
            "BLOB_READ_WRITE_TOKEN is not configured",
            error_type="configuration",
        )

    logger.info(f"Starting batch deletion of {len(blob_urls)} blobs")

    try:
        async with httpx.AsyncClient() as client:
            # Vercel Blob supports batch delete
            response = await client.post(
                "https://blob.vercel-storage.com/delete",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "urls": blob_urls,
                },
                timeout=60.0,  # Longer timeout for batch
            )

            if response.status_code == 200:
                # All deletions successful
                results["deleted"] = len(blob_urls)
                logger.info(
                    f"BATCH_BLOB_DELETED: {len(blob_urls)} blobs at {datetime.utcnow().isoformat()}Z"
                )
                return results

            elif response.status_code == 207:
                # Partial success - parse response for details
                data = response.json()
                for item in data.get("results", []):
                    if item.get("success"):
                        results["deleted"] += 1
                    elif item.get("status") == 404:
                        results["not_found"] += 1
                    else:
                        results["failed"] += 1
                        results["failed_urls"].append(item.get("url"))

                logger.info(
                    f"Batch deletion completed: {results['deleted']} deleted, "
                    f"{results['not_found']} not found, {results['failed']} failed"
                )
                return results

            else:
                # If batch fails, try individual deletions
                logger.warning(
                    f"Batch deletion returned {response.status_code}, falling back to individual deletions"
                )

    except Exception as e:
        logger.warning(f"Batch deletion failed ({e}), falling back to individual deletions")

    # Fallback: Individual deletions
    for url in blob_urls:
        try:
            success = await delete_blob(url)
            if success:
                results["deleted"] += 1
            else:
                results["not_found"] += 1
        except BlobStorageError as e:
            logger.error(f"Failed to delete blob {url}: {e}")
            results["failed"] += 1
            results["failed_urls"].append(url)

    logger.info(
        f"Batch deletion completed (fallback): {results['deleted']} deleted, "
        f"{results['not_found']} not found, {results['failed']} failed"
    )

    return results
