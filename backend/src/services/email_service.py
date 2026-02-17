"""
Email service for sending transactional emails via Resend API.

This service provides email delivery functionality with professional HTML templates,
retry logic, and comprehensive error handling.

Features:
- Verification code emails with 6-digit codes
- Meal plan delivery emails with PDF attachment (T082)
- HTML email templates with green theme (#22c55e)
- Plain text fallback for non-HTML clients
- Retry logic with exponential backoff (3 attempts: 2s, 4s, 8s) (T083)
- Idempotency checks to prevent duplicate sends (T085)
- Manual resolution queue routing on failure (T083)
- Comprehensive error handling and logging
- Environment-based configuration (RESEND_API_KEY, RESEND_FROM_EMAIL)

Dependencies:
- resend: Python SDK for Resend API
- Environment variables: RESEND_API_KEY, RESEND_FROM_EMAIL

Usage:
    from src.services.email_service import send_verification_email, send_delivery_email

    # Verification email
    result = await send_verification_email(
        to_email="user@example.com",
        verification_code="123456"
    )

    # Delivery email with PDF
    result = await send_delivery_email(
        to_email="user@example.com",
        calorie_target=1800,
        pdf_bytes=pdf_content,
        pdf_filename="keto-meal-plan.pdf"
    )

    if result["success"]:
        print(f"Email sent! Message ID: {result['message_id']}")
    else:
        print(f"Failed to send email: {result['error']}")
"""

import base64
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import resend

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "noreply@ketomealplan.com")

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]  # Exponential backoff: 2s, 4s, 8s


def _generate_html_template(verification_code: str) -> str:
    """
    Generate HTML email template for verification code.

    Args:
        verification_code: 6-digit verification code

    Returns:
        str: HTML email content with green theme and mobile-responsive design
    """
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Verification Code</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .header {{
            background-color: #22c55e;
            color: #ffffff;
            padding: 40px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .content {{
            padding: 40px 30px;
            text-align: center;
        }}
        .content p {{
            color: #374151;
            font-size: 16px;
            line-height: 1.6;
            margin: 0 0 20px 0;
        }}
        .code-container {{
            background-color: #f9fafb;
            border: 2px solid #22c55e;
            border-radius: 8px;
            padding: 30px 20px;
            margin: 30px 0;
        }}
        .code {{
            font-size: 48px;
            font-weight: 700;
            color: #22c55e;
            letter-spacing: 8px;
            margin: 0;
            font-family: 'Courier New', monospace;
        }}
        .expiry-warning {{
            background-color: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 16px 20px;
            margin: 30px 0;
            text-align: left;
        }}
        .expiry-warning p {{
            color: #92400e;
            margin: 0;
            font-size: 14px;
        }}
        .expiry-warning strong {{
            color: #78350f;
            font-weight: 600;
        }}
        .footer {{
            background-color: #f9fafb;
            padding: 30px 30px;
            text-align: center;
            border-top: 1px solid #e5e7eb;
        }}
        .footer p {{
            color: #6b7280;
            font-size: 14px;
            margin: 5px 0;
        }}
        .footer a {{
            color: #22c55e;
            text-decoration: none;
            font-weight: 500;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
        @media only screen and (max-width: 600px) {{
            .container {{
                margin: 20px 10px;
            }}
            .header h1 {{
                font-size: 24px;
            }}
            .code {{
                font-size: 36px;
                letter-spacing: 6px;
            }}
            .content {{
                padding: 30px 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Keto Meal Plan</h1>
        </div>
        <div class="content">
            <p>You requested a verification code to access your personalized keto meal plan.</p>
            <p>Enter the code below to verify your email address:</p>

            <div class="code-container">
                <p class="code">{verification_code}</p>
            </div>

            <div class="expiry-warning">
                <p><strong>⏰ Important:</strong> This code expires in 10 minutes for security reasons.</p>
            </div>

            <p>If you didn't request this code, you can safely ignore this email.</p>
        </div>
        <div class="footer">
            <p>Need help? Contact us at <a href="mailto:support@ketomealplan.com">support@ketomealplan.com</a></p>
            <p>&copy; 2026 Keto Meal Plan. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""


def _generate_plain_text_template(verification_code: str) -> str:
    """
    Generate plain text email template for verification code (fallback).

    Args:
        verification_code: 6-digit verification code

    Returns:
        str: Plain text email content
    """
    return f"""
KETO MEAL PLAN - EMAIL VERIFICATION
=====================================

You requested a verification code to access your personalized keto meal plan.

Your verification code is:

    {verification_code}

⏰ IMPORTANT: This code expires in 10 minutes for security reasons.

Enter this code on the website to verify your email address and continue.

If you didn't request this code, you can safely ignore this email.

---
Need help? Contact us at support@ketomealplan.com
© 2026 Keto Meal Plan. All rights reserved.
"""


async def send_verification_email(
    to_email: str,
    verification_code: str
) -> Dict[str, Any]:
    """
    Send verification code email via Resend API with retry logic.

    This function sends a professional HTML email with the verification code,
    including plain text fallback for non-HTML clients. It implements retry
    logic with exponential backoff to handle transient failures.

    Args:
        to_email: Recipient email address
        verification_code: 6-digit verification code

    Returns:
        Dict with keys:
        - success (bool): True if email was sent successfully
        - message_id (str): Resend message ID (if successful)
        - error (str): Error message (if failed)
        - attempts (int): Number of attempts made

    Examples:
        >>> result = await send_verification_email("user@example.com", "123456")
        >>> if result["success"]:
        ...     print(f"Email sent! Message ID: {result['message_id']}")
        ... else:
        ...     print(f"Failed: {result['error']}")

    Error Cases:
        - Missing API key: {"success": False, "error": "RESEND_API_KEY not configured"}
        - Invalid email: {"success": False, "error": "Invalid recipient email"}
        - API error: {"success": False, "error": "Resend API error: ..."}
        - All retries failed: {"success": False, "error": "Failed after 3 attempts: ..."}

    Retry Logic:
        - Attempts: 3 (initial + 2 retries)
        - Delays: 2s, 4s, 8s (exponential backoff)
        - Retries on: Network errors, rate limits, temporary API failures
        - No retry on: Invalid API key, invalid email format
    """
    # Validate environment configuration
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY environment variable not set")
        return {
            "success": False,
            "error": "Email service not configured. Please contact support.",
            "attempts": 0,
        }

    # Configure Resend API
    resend.api_key = RESEND_API_KEY

    # Generate email templates
    html_content = _generate_html_template(verification_code)
    text_content = _generate_plain_text_template(verification_code)

    # Retry loop with exponential backoff
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f"Sending verification email to {to_email} (attempt {attempt}/{MAX_RETRIES})"
            )

            # Send email via Resend API
            response = resend.Emails.send({
                "from": RESEND_FROM_EMAIL,
                "to": to_email,
                "subject": "Your Verification Code",
                "html": html_content,
                "text": text_content,
            })

            # Success - extract message ID
            message_id = response.get("id", "unknown")
            logger.info(
                f"Verification email sent successfully to {to_email} "
                f"(message_id: {message_id}, attempt: {attempt})"
            )

            return {
                "success": True,
                "message_id": message_id,
                "attempts": attempt,
            }

        except resend.exceptions.ResendError as e:
            # Resend-specific errors
            error_message = str(e)
            last_error = error_message

            # Check if error is retryable
            is_retryable = _is_retryable_error(error_message)

            logger.warning(
                f"Resend API error on attempt {attempt}/{MAX_RETRIES} "
                f"for {to_email}: {error_message} "
                f"(retryable: {is_retryable})"
            )

            # Don't retry on non-retryable errors (invalid API key, bad email format)
            if not is_retryable:
                return {
                    "success": False,
                    "error": f"Email delivery failed: {error_message}",
                    "attempts": attempt,
                }

            # Retry with exponential backoff
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1]
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

        except Exception as e:
            # Unexpected errors (network issues, etc.)
            error_message = f"{type(e).__name__}: {str(e)}"
            last_error = error_message

            logger.warning(
                f"Unexpected error on attempt {attempt}/{MAX_RETRIES} "
                f"for {to_email}: {error_message}"
            )

            # Retry on unexpected errors
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1]
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

    # All retries exhausted
    logger.error(
        f"Failed to send verification email to {to_email} after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )

    return {
        "success": False,
        "error": f"Email delivery failed after {MAX_RETRIES} attempts. Please try again later.",
        "attempts": MAX_RETRIES,
    }


def _is_retryable_error(error_message: str) -> bool:
    """
    Determine if a Resend API error is retryable.

    Non-retryable errors (client-side issues):
    - Invalid API key
    - Invalid email format
    - Invalid from address
    - Missing required fields

    Retryable errors (server-side issues):
    - Rate limiting
    - Temporary server errors
    - Network timeouts
    - Service unavailable

    Args:
        error_message: Error message from Resend API

    Returns:
        bool: True if error should be retried, False otherwise
    """
    error_lower = error_message.lower()

    # Non-retryable errors (client-side issues)
    non_retryable_keywords = [
        "invalid api key",
        "api key",
        "authentication",
        "unauthorized",
        "invalid email",
        "invalid recipient",
        "invalid from",
        "missing required",
        "bad request",
        "validation error",
    ]

    for keyword in non_retryable_keywords:
        if keyword in error_lower:
            return False

    # Retryable errors (server-side issues)
    retryable_keywords = [
        "rate limit",
        "too many requests",
        "server error",
        "service unavailable",
        "timeout",
        "temporarily unavailable",
        "503",
        "502",
        "429",
    ]

    for keyword in retryable_keywords:
        if keyword in error_lower:
            return True

    # Default: retry on unknown errors (safer approach)
    return True


# Base URL for links (from environment variable)
APP_URL = os.getenv("APP_URL", "http://localhost:3000")

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _load_delivery_template(template_name: str) -> str:
    """
    Load a delivery email template from the templates directory.

    Args:
        template_name: Template filename (e.g., "delivery_email.html")

    Returns:
        str: Template content

    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Email template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def _render_delivery_template(
    template_content: str,
    calorie_target: int,
    pdf_download_url: str,
    magic_link_url: str,
    create_account_url: str,
    user_email: str,
) -> str:
    """
    Render delivery email template with placeholder substitution.

    Args:
        template_content: Raw template string with placeholders
        calorie_target: Daily calorie target to display
        pdf_download_url: URL for PDF download (on-demand signed URL endpoint)
        magic_link_url: URL to request magic link for recovery
        create_account_url: URL to create account for permanent access
        user_email: User's email address to display in footer

    Returns:
        str: Rendered template with all placeholders replaced
    """
    return (
        template_content
        .replace("{calorie_target}", str(calorie_target))
        .replace("{pdf_download_url}", pdf_download_url)
        .replace("{magic_link_url}", magic_link_url)
        .replace("{create_account_url}", create_account_url)
        .replace("{user_email}", user_email)
    )


def _build_delivery_urls(
    payment_id: str,
    user_email: str,
    meal_plan_id: Optional[str] = None
) -> Dict[str, str]:
    """
    Build all URLs needed for the delivery email.

    Per FR-E-002:
    - PDF download link points to /api/download-pdf endpoint which generates
      fresh signed URL on-demand (not a pre-signed URL)
    - Magic link points to /recover-plan page
    - Account creation link includes signed token with pre-filled email (T100)

    Args:
        payment_id: Paddle payment ID for download URL
        user_email: User's email for account creation URL
        meal_plan_id: Optional meal plan ID to encode in signup token

    Returns:
        Dict with pdf_download_url, magic_link_url, create_account_url
    """
    from urllib.parse import quote
    from src.services.auth_service import create_signup_token

    # Generate signed signup token encoding email, meal_plan_id, payment_id (T100)
    # Token expires in 7 days, encodes user_email for readonly field (FR-R-001)
    signup_token = create_signup_token(
        email=user_email,
        meal_plan_id=meal_plan_id,
        payment_id=payment_id,
    )

    encoded_email = quote(user_email, safe="")
    encoded_token = quote(signup_token, safe="")

    return {
        "pdf_download_url": f"{APP_URL}/api/download-pdf?payment_id={payment_id}",
        "magic_link_url": f"{APP_URL}/recover-plan",
        "create_account_url": f"{APP_URL}/create-account?token={encoded_token}",
    }


async def send_delivery_email(
    to_email: str,
    calorie_target: int,
    pdf_bytes: bytes,
    pdf_filename: str,
    payment_id: str,
    email_already_sent: bool = False,
    meal_plan_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send meal plan delivery email via Resend API with PDF attachment.

    This function sends a professional HTML email with the generated PDF meal plan
    attached, including download link, recovery instructions, and optional account
    creation link. It implements:
    - T082: Email sending with Resend, PDF attachment, template rendering
    - T083: Retry logic (3 attempts, exponential backoff: 2s, 4s, 8s)
    - T084: Returns sent_at timestamp for caller to update database
    - T085: Idempotency check to prevent duplicate sends on webhook retries
    - T100: Account creation link with signed token

    Args:
        to_email: Recipient email address
        calorie_target: Daily calorie target to display in email
        pdf_bytes: Generated PDF content as bytes
        pdf_filename: Filename for PDF attachment (e.g., "keto-meal-plan-30-days.pdf")
        payment_id: Paddle payment ID for building download URL
        email_already_sent: If True, return early with success (idempotency check, T085)
        meal_plan_id: Optional meal plan ID to encode in signup token (T100)

    Returns:
        Dict with keys:
        - success (bool): True if email was sent successfully
        - message_id (str): Resend message ID (if successful)
        - sent_at (datetime): Timestamp when email was sent (for T084, caller updates DB)
        - error (str): Error message (if failed)
        - attempts (int): Number of attempts made
        - requires_manual_resolution (bool): True if failed after all retries (T083)
        - manual_resolution_info (dict): Info for creating manual_resolution entry (T083)

    Examples:
        >>> result = await send_delivery_email(
        ...     to_email="user@example.com",
        ...     calorie_target=1800,
        ...     pdf_bytes=pdf_content,
        ...     pdf_filename="keto-meal-plan.pdf",
        ...     payment_id="txn_01234567890"
        ... )
        >>> if result["success"]:
        ...     # Update database with sent_at timestamp
        ...     meal_plan.email_sent_at = result["sent_at"]
        ... elif result.get("requires_manual_resolution"):
        ...     # Create manual resolution queue entry
        ...     create_manual_resolution(result["manual_resolution_info"])

    Idempotency (T085):
        If email_already_sent=True (checked by caller from meal_plan.email_sent_at),
        function returns early with success to prevent duplicate sends on webhook retries.

    Retry Logic (T083):
        - Attempts: 3 (initial + 2 retries)
        - Delays: 2s, 4s, 8s (exponential backoff)
        - Retries on: Network errors, rate limits, temporary API failures
        - No retry on: Invalid API key, invalid email format
        - On all retries failed: Returns info for manual_resolution queue entry

    Template Placeholders:
        - {calorie_target}: Daily calorie target
        - {pdf_download_url}: On-demand signed URL endpoint
        - {magic_link_url}: Recovery page URL
        - {create_account_url}: Account creation URL with pre-filled email
        - {user_email}: User's email address

    FR-E-001 to FR-E-005 Compliance:
        - FR-E-001: Sends transactional email with PDF attached
        - FR-E-002: Includes download link, recovery instructions, account creation link
        - FR-E-003: Uses professional branded templates (green #22c55e)
        - FR-E-004: Idempotent via email_already_sent parameter
        - FR-E-005: Retries with exponential backoff, routes to manual_resolution on failure
    """
    # T085: Idempotency check - prevent duplicate sends on webhook retries
    if email_already_sent:
        logger.info(
            f"Email already sent for payment, skipping duplicate send "
            f"(to_email={to_email}, payment_id={payment_id})"
        )
        return {
            "success": True,
            "message_id": "already_sent",
            "sent_at": None,  # No new send, so no timestamp
            "error": None,
            "attempts": 0,
            "requires_manual_resolution": False,
        }

    # Validate environment configuration
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY environment variable not set")
        return {
            "success": False,
            "message_id": None,
            "sent_at": None,
            "error": "Email service not configured. Please contact support.",
            "attempts": 0,
            "requires_manual_resolution": True,
            "manual_resolution_info": {
                "payment_id": payment_id,
                "user_email": to_email,
                "issue_type": "email_delivery_failed",
                "error_details": "RESEND_API_KEY not configured",
            },
        }

    # Configure Resend API
    resend.api_key = RESEND_API_KEY

    # Build URLs for email links (T100: includes signed signup token)
    urls = _build_delivery_urls(payment_id, to_email, meal_plan_id)

    # Load and render email templates
    try:
        html_template = _load_delivery_template("delivery_email.html")
        text_template = _load_delivery_template("delivery_email.txt")

        html_content = _render_delivery_template(
            html_template,
            calorie_target=calorie_target,
            pdf_download_url=urls["pdf_download_url"],
            magic_link_url=urls["magic_link_url"],
            create_account_url=urls["create_account_url"],
            user_email=to_email,
        )

        text_content = _render_delivery_template(
            text_template,
            calorie_target=calorie_target,
            pdf_download_url=urls["pdf_download_url"],
            magic_link_url=urls["magic_link_url"],
            create_account_url=urls["create_account_url"],
            user_email=to_email,
        )
    except FileNotFoundError as e:
        logger.error(f"Email template not found: {e}")
        return {
            "success": False,
            "message_id": None,
            "sent_at": None,
            "error": f"Email template error: {e}",
            "attempts": 0,
            "requires_manual_resolution": True,
            "manual_resolution_info": {
                "payment_id": payment_id,
                "user_email": to_email,
                "issue_type": "email_delivery_failed",
                "error_details": f"Template not found: {e}",
            },
        }

    # Encode PDF as base64 for attachment
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

    # T083: Retry loop with exponential backoff (2s, 4s, 8s)
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f"Sending delivery email to {to_email} "
                f"(attempt {attempt}/{MAX_RETRIES}, payment_id={payment_id})"
            )

            # Send email via Resend API with PDF attachment
            response = resend.Emails.send({
                "from": RESEND_FROM_EMAIL,
                "to": to_email,
                "subject": "Your Custom Keto Plan - Ready to Transform!",
                "html": html_content,
                "text": text_content,
                "attachments": [
                    {
                        "filename": pdf_filename,
                        "content": pdf_base64,
                    }
                ],
            })

            # T084: Capture sent_at timestamp for caller to update database
            sent_at = datetime.utcnow()

            # Success - extract message ID
            message_id = response.get("id", "unknown")
            logger.info(
                f"Delivery email sent successfully to {to_email} "
                f"(message_id={message_id}, attempt={attempt}, payment_id={payment_id})"
            )

            return {
                "success": True,
                "message_id": message_id,
                "sent_at": sent_at,  # T084: Caller uses this to update meal_plan.email_sent_at
                "error": None,
                "attempts": attempt,
                "requires_manual_resolution": False,
            }

        except resend.exceptions.ResendError as e:
            # Resend-specific errors
            error_message = str(e)
            last_error = error_message

            # Check if error is retryable
            is_retryable = _is_retryable_error(error_message)

            logger.warning(
                f"Resend API error on attempt {attempt}/{MAX_RETRIES} "
                f"for {to_email}: {error_message} "
                f"(retryable={is_retryable}, payment_id={payment_id})"
            )

            # Don't retry on non-retryable errors (invalid API key, bad email format)
            if not is_retryable:
                return {
                    "success": False,
                    "message_id": None,
                    "sent_at": None,
                    "error": f"Email delivery failed: {error_message}",
                    "attempts": attempt,
                    "requires_manual_resolution": True,
                    "manual_resolution_info": {
                        "payment_id": payment_id,
                        "user_email": to_email,
                        "issue_type": "email_delivery_failed",
                        "error_details": error_message,
                    },
                }

            # T083: Retry with exponential backoff
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1]
                logger.info(f"Retrying email send in {delay} seconds...")
                await asyncio.sleep(delay)

        except Exception as e:
            # Unexpected errors (network issues, etc.)
            error_message = f"{type(e).__name__}: {str(e)}"
            last_error = error_message

            logger.warning(
                f"Unexpected error on attempt {attempt}/{MAX_RETRIES} "
                f"for {to_email}: {error_message} (payment_id={payment_id})"
            )

            # T083: Retry on unexpected errors
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1]
                logger.info(f"Retrying email send in {delay} seconds...")
                await asyncio.sleep(delay)

    # T083: All retries exhausted - return info for manual_resolution queue entry
    logger.error(
        f"Failed to send delivery email to {to_email} after {MAX_RETRIES} attempts. "
        f"Last error: {last_error} (payment_id={payment_id})"
    )

    return {
        "success": False,
        "message_id": None,
        "sent_at": None,
        "error": f"Email delivery failed after {MAX_RETRIES} attempts. Please try again later.",
        "attempts": MAX_RETRIES,
        "requires_manual_resolution": True,
        "manual_resolution_info": {
            "payment_id": payment_id,
            "user_email": to_email,
            "issue_type": "email_delivery_failed",
            "error_details": last_error,
        },
    }


async def send_magic_link_email(
    to_email: str,
    magic_link_url: str,
) -> Dict[str, Any]:
    """
    Send magic link recovery email via Resend API with retry logic.

    This function sends a professional HTML email with a magic link for
    passwordless plan recovery. It implements retry logic with exponential
    backoff to handle transient failures.

    Args:
        to_email: Recipient email address
        magic_link_url: Full magic link URL with token

    Returns:
        Dict with keys:
        - success (bool): True if email was sent successfully
        - message_id (str): Resend message ID (if successful)
        - error (str): Error message (if failed)
        - attempts (int): Number of attempts made

    Examples:
        >>> result = await send_magic_link_email(
        ...     to_email="user@example.com",
        ...     magic_link_url="https://yourdomain.com/verify-magic-link?token=abc123..."
        ... )
        >>> if result["success"]:
        ...     print(f"Email sent! Message ID: {result['message_id']}")
        ... else:
        ...     print(f"Failed: {result['error']}")

    Error Cases:
        - Missing API key: {"success": False, "error": "RESEND_API_KEY not configured"}
        - Invalid email: {"success": False, "error": "Invalid recipient email"}
        - API error: {"success": False, "error": "Resend API error: ..."}
        - All retries failed: {"success": False, "error": "Failed after 3 attempts: ..."}

    Retry Logic:
        - Attempts: 3 (initial + 2 retries)
        - Delays: 2s, 4s, 8s (exponential backoff)
        - Retries on: Network errors, rate limits, temporary API failures
        - No retry on: Invalid API key, invalid email format

    Reference:
        Phase 7.1 - Magic link generation (T090-T093)
    """
    # Validate environment configuration
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY environment variable not set")
        return {
            "success": False,
            "error": "Email service not configured. Please contact support.",
            "attempts": 0,
        }

    # Configure Resend API
    resend.api_key = RESEND_API_KEY

    # Load and render email templates
    try:
        html_template = _load_delivery_template("magic_link_email.html")
        text_template = _load_delivery_template("magic_link_email.txt")

        html_content = (
            html_template
            .replace("{magic_link_url}", magic_link_url)
            .replace("{user_email}", to_email)
        )

        text_content = (
            text_template
            .replace("{magic_link_url}", magic_link_url)
            .replace("{user_email}", to_email)
        )
    except FileNotFoundError as e:
        logger.error(f"Email template not found: {e}")
        return {
            "success": False,
            "error": f"Email template error: {e}",
            "attempts": 0,
        }

    # Retry loop with exponential backoff
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f"Sending magic link email to {to_email} (attempt {attempt}/{MAX_RETRIES})"
            )

            # Send email via Resend API
            response = resend.Emails.send({
                "from": RESEND_FROM_EMAIL,
                "to": to_email,
                "subject": "Access Your Keto Meal Plan - Magic Link Inside",
                "html": html_content,
                "text": text_content,
            })

            # Success - extract message ID
            message_id = response.get("id", "unknown")
            logger.info(
                f"Magic link email sent successfully to {to_email} "
                f"(message_id: {message_id}, attempt: {attempt})"
            )

            return {
                "success": True,
                "message_id": message_id,
                "attempts": attempt,
            }

        except resend.exceptions.ResendError as e:
            # Resend-specific errors
            error_message = str(e)
            last_error = error_message

            # Check if error is retryable
            is_retryable = _is_retryable_error(error_message)

            logger.warning(
                f"Resend API error on attempt {attempt}/{MAX_RETRIES} "
                f"for {to_email}: {error_message} "
                f"(retryable: {is_retryable})"
            )

            # Don't retry on non-retryable errors (invalid API key, bad email format)
            if not is_retryable:
                return {
                    "success": False,
                    "error": f"Email delivery failed: {error_message}",
                    "attempts": attempt,
                }

            # Retry with exponential backoff
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1]
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

        except Exception as e:
            # Unexpected errors (network issues, etc.)
            error_message = f"{type(e).__name__}: {str(e)}"
            last_error = error_message

            logger.warning(
                f"Unexpected error on attempt {attempt}/{MAX_RETRIES} "
                f"for {to_email}: {error_message}"
            )

            # Retry on unexpected errors
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1]
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

    # All retries exhausted
    logger.error(
        f"Failed to send magic link email to {to_email} after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )

    return {
        "success": False,
        "error": f"Email delivery failed after {MAX_RETRIES} attempts. Please try again later.",
        "attempts": MAX_RETRIES,
    }


def _generate_sla_missed_refund_html_template(amount: float, payment_id: str) -> str:
    """
    Generate HTML email template for SLA missed refund notification.

    Args:
        amount: Refund amount
        payment_id: Paddle payment ID

    Returns:
        str: HTML email content with professional refund notification template
    """
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Refund Issued - Service Issue</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .header {{
            background-color: #ef4444;
            color: #ffffff;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .content {{
            padding: 40px 30px;
            text-align: center;
        }}
        .content p {{
            color: #374151;
            font-size: 16px;
            line-height: 1.6;
            margin: 0 0 20px 0;
        }}
        .success-container {{
            background-color: #d1fae5;
            border: 2px solid #10b981;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            text-align: left;
        }}
        .success-container p {{
            color: #065f46;
            margin: 0;
            font-size: 15px;
        }}
        .refund-section {{
            background-color: #f9fafb;
            border-radius: 8px;
            padding: 25px 20px;
            margin: 30px 0;
            text-align: center;
        }}
        .refund-amount {{
            font-size: 32px;
            font-weight: 700;
            color: #10b981;
            margin: 10px 0;
        }}
        .payment-id {{
            font-size: 14px;
            color: #6b7280;
            margin-top: 10px;
            word-break: break-all;
        }}
        .footer {{
            background-color: #f9fafb;
            padding: 30px 30px;
            text-align: center;
            border-top: 1px solid #e5e7eb;
        }}
        .footer p {{
            color: #6b7280;
            font-size: 14px;
            margin: 5px 0;
        }}
        .footer a {{
            color: #22c55e;
            text-decoration: none;
            font-weight: 500;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
        @media only screen and (max-width: 600px) {{
            .container {{
                margin: 20px 10px;
            }}
            .header h1 {{
                font-size: 24px;
            }}
            .refund-amount {{
                font-size: 28px;
            }}
            .content {{
                padding: 30px 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Service Issue - Refund Issued</h1>
        </div>
        <div class="content">
            <p>We sincerely apologize for the delay in delivering your service.</p>
            <p>Due to missing our service level agreement (SLA) deadline, we've automatically issued a refund for your recent purchase.</p>

            <div class="refund-section">
                <p style="font-size: 18px; font-weight: 600; color: #374151;">Automatic refund processed:</p>
                <div class="refund-amount">${amount:.2f}</div>
                <div class="payment-id">Payment ID: {payment_id}</div>
            </div>

            <div class="success-container">
                <p>✓ The refund has been processed and will be returned to your original payment method within 5-10 business days, depending on your bank's policies.</p>
                <p>✓ If you don't see the refund within this timeframe, please contact your payment provider or reach out to our support team.</p>
            </div>

            <p>If you still wish to receive your keto meal plan, please contact our support team at the email below.</p>

            <p>We're committed to improving our service and appreciate your patience.</p>
        </div>
        <div class="footer">
            <p>Need help? Contact us at <a href="mailto:support@ketomealplan.com">support@ketomealplan.com</a></p>
            <p>&copy; 2026 Keto Meal Plan. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""


def _generate_sla_missed_refund_plain_text_template(amount: float, payment_id: str) -> str:
    """
    Generate plain text email template for SLA missed refund notification.

    Args:
        amount: Refund amount
        payment_id: Paddle payment ID

    Returns:
        str: Plain text email content
    """
    return f"""
KETO MEAL PLAN - REFUND ISSUED
==============================

We sincerely apologize for the delay in delivering your service.

Due to missing our service level agreement (SLA) deadline, we've automatically issued a refund for your recent purchase.

REFUND DETAILS:
    Amount: ${amount:.2f}
    Payment ID: {payment_id}

REFUND PROCESSING:
    - The refund has been processed and will be returned to your original payment method
    - Please allow 5-10 business days for the refund to appear (bank processing times vary)
    - If you don't see the refund within this timeframe, contact your payment provider or our support

If you still wish to receive your keto meal plan, please contact our support team.

We're committed to improving our service and appreciate your patience.

---
Need help? Contact us at support@ketomealplan.com
© 2026 Keto Meal Plan. All rights reserved.
"""


async def send_sla_missed_refund_email(
    to_email: str,
    payment_id: str,
    amount: float
) -> Dict[str, Any]:
    """
    Send SLA missed refund notification email via Resend API with retry logic.

    This function sends a professional HTML email notifying the customer about
    an automatic refund issued due to an SLA miss in service delivery.
    It implements retry logic with exponential backoff to handle transient failures.

    Args:
        to_email: Recipient email address
        payment_id: Paddle payment ID that was refunded
        amount: The refund amount

    Returns:
        Dict with keys:
        - success (bool): True if email was sent successfully
        - message_id (str): Resend message ID (if successful)
        - error (str): Error message (if failed)
        - attempts (int): Number of attempts made

    Examples:
        >>> result = await send_sla_missed_refund_email(
        ...     to_email="user@example.com",
        ...     payment_id="txn_0123456789",
        ...     amount=47.00
        ... )
        >>> if result["success"]:
        ...     print(f"Refund email sent! Message ID: {result['message_id']}")
        ... else:
        ...     print(f"Failed: {result['error']}")
    """
    # Validate environment configuration
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY environment variable not set")
        return {
            "success": False,
            "error": "Email service not configured. Please contact support.",
            "attempts": 0,
        }

    # Validate input values
    if amount <= 0:
        logger.error(f"Invalid refund amount: {amount}")
        return {
            "success": False,
            "error": "Invalid refund amount.",
            "attempts": 0,
        }

    # Configure Resend API
    resend.api_key = RESEND_API_KEY

    # Generate email templates
    html_content = _generate_sla_missed_refund_html_template(amount, payment_id)
    text_content = _generate_sla_missed_refund_plain_text_template(amount, payment_id)

    # Retry loop with exponential backoff
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f"Sending SLA missed refund email to {to_email} "
                f"(attempt {attempt}/{MAX_RETRIES}, payment_id={payment_id})"
            )

            # Send email via Resend API
            response = resend.Emails.send({
                "from": RESEND_FROM_EMAIL,
                "to": to_email,
                "subject": "Refund Issued - Service Delivery Delay",
                "html": html_content,
                "text": text_content,
            })

            # Success - extract message ID
            message_id = response.get("id", "unknown")
            logger.info(
                f"SLA missed refund email sent successfully to {to_email} "
                f"(message_id: {message_id}, attempt: {attempt})"
            )

            return {
                "success": True,
                "message_id": message_id,
                "attempts": attempt,
            }

        except resend.exceptions.ResendError as e:
            # Resend-specific errors
            error_message = str(e)
            last_error = error_message

            # Check if error is retryable
            is_retryable = _is_retryable_error(error_message)

            logger.warning(
                f"Resend API error on attempt {attempt}/{MAX_RETRIES} "
                f"for {to_email}: {error_message} "
                f"(retryable: {is_retryable})"
            )

            # Don't retry on non-retryable errors (invalid API key, bad email format)
            if not is_retryable:
                return {
                    "success": False,
                    "error": f"Email delivery failed: {error_message}",
                    "attempts": attempt,
                }

            # Retry with exponential backoff
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1]
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

        except Exception as e:
            # Unexpected errors (network issues, etc.)
            error_message = f"{type(e).__name__}: {str(e)}"
            last_error = error_message

            logger.warning(
                f"Unexpected error on attempt {attempt}/{MAX_RETRIES} "
                f"for {to_email}: {error_message}"
            )

            # Retry on unexpected errors
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1]
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

    # All retries exhausted
    logger.error(
        f"Failed to send SLA missed refund email to {to_email} after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )

    return {
        "success": False,
        "error": f"Email delivery failed after {MAX_RETRIES} attempts. Please try again later.",
        "attempts": MAX_RETRIES,
    }