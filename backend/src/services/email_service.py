"""
Email service for sending verification codes via Resend API.

This service provides email delivery functionality with professional HTML templates,
retry logic, and comprehensive error handling.

Features:
- HTML email templates with green theme (#22c55e)
- Plain text fallback for non-HTML clients
- Retry logic with exponential backoff (3 attempts: 2s, 4s, 8s)
- Comprehensive error handling and logging
- Environment-based configuration (RESEND_API_KEY, RESEND_FROM_EMAIL)

Dependencies:
- resend: Python SDK for Resend API
- Environment variables: RESEND_API_KEY, RESEND_FROM_EMAIL

Usage:
    from src.services.email_service import send_verification_email

    result = await send_verification_email(
        to_email="user@example.com",
        verification_code="123456"
    )

    if result["success"]:
        print(f"Email sent! Message ID: {result['message_id']}")
    else:
        print(f"Failed to send email: {result['error']}")
"""

import os
import asyncio
import logging
from typing import Dict, Any

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
