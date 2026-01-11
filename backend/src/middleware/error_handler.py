"""
Global Error Handler Middleware

Provides consistent error responses across the entire API.
All exceptions are caught, logged, and transformed into structured JSON responses.

Error Response Format:
{
    "error": {
        "code": "error_code",
        "message": "User-friendly error message",
        "details": {
            // Optional additional context
        }
    }
}

Error Handling Strategy:
- Catch all exceptions to prevent crashes
- Log errors with full context for debugging
- Return user-safe error messages (no internal details)
- Track errors in Sentry for monitoring
- Provide actionable error information
- Use consistent HTTP status codes

Security Considerations:
- Never expose internal server details in error messages
- Sanitize error messages to prevent information leakage
- Log full error details server-side only
- Use generic messages for unexpected errors
"""

import logging
from typing import Union, Dict, Any, List

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError
import sentry_sdk

logger = logging.getLogger(__name__)


def create_error_response(
    code: str,
    message: str,
    status_code: int,
    details: Union[Dict[str, Any], List[Dict[str, Any]], None] = None,
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        code: Error code (e.g., "validation_error", "not_found", "internal_error")
        message: User-friendly error message
        status_code: HTTP status code
        details: Optional additional error context

    Returns:
        JSONResponse: Structured error response
    """
    error_content = {
        "error": {
            "code": code,
            "message": message,
        }
    }

    if details:
        error_content["error"]["details"] = details

    return JSONResponse(
        status_code=status_code,
        content=error_content,
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for all unhandled exceptions.

    Catches any exception that wasn't handled by specific exception handlers.
    This is the last line of defense to prevent server crashes.

    Args:
        request: FastAPI request object
        exc: The unhandled exception

    Returns:
        JSONResponse: Generic error response (500 Internal Server Error)
    """
    # Log the full exception with stack trace
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client": request.client.host if request.client else None,
        },
    )

    # Capture exception in Sentry for monitoring
    sentry_sdk.capture_exception(exc)

    # Return generic error message (don't expose internal details)
    return create_error_response(
        code="internal_error",
        message="An unexpected error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details={
            "request_id": request.headers.get("x-request-id"),
        } if request.headers.get("x-request-id") else None,
    )


async def http_exception_handler(
    request: Request,
    exc: Union[HTTPException, StarletteHTTPException]
) -> JSONResponse:
    """
    Handler for HTTPException (raised by FastAPI/Starlette).

    Provides consistent error format for all HTTP exceptions like:
    - 400 Bad Request
    - 401 Unauthorized
    - 403 Forbidden
    - 404 Not Found
    - 422 Unprocessable Entity
    - 500 Internal Server Error

    Args:
        request: FastAPI request object
        exc: HTTPException instance

    Returns:
        JSONResponse: Structured error response
    """
    # Log the HTTP exception (info level for client errors, error level for server errors)
    log_level = logging.ERROR if exc.status_code >= 500 else logging.INFO
    logger.log(
        log_level,
        f"HTTP {exc.status_code} in {request.method} {request.url.path}: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else None,
        },
    )

    # Capture server errors (5xx) in Sentry
    if exc.status_code >= 500:
        sentry_sdk.capture_exception(exc)

    # Map status codes to error codes
    error_code_map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "unprocessable_entity",
        429: "rate_limit_exceeded",
        500: "internal_error",
        502: "bad_gateway",
        503: "service_unavailable",
        504: "gateway_timeout",
    }

    error_code = error_code_map.get(exc.status_code, "http_error")

    # Handle detail as dict or string
    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", str(exc.detail))
        details = exc.detail.get("details")
    else:
        message = str(exc.detail)
        details = None

    return create_error_response(
        code=error_code,
        message=message,
        status_code=exc.status_code,
        details=details,
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError],
) -> JSONResponse:
    """
    Handler for Pydantic validation errors.

    Provides user-friendly error messages for request validation failures.
    Transforms Pydantic validation errors into structured error responses.

    Common Validation Errors:
    - Missing required fields
    - Invalid data types
    - Value constraints (min/max, regex)
    - Custom validation failures

    Args:
        request: FastAPI request object
        exc: RequestValidationError or Pydantic ValidationError

    Returns:
        JSONResponse: Structured validation error response (422 Unprocessable Entity)
    """
    # Extract validation errors
    errors = []

    for error in exc.errors():
        # Get field location (e.g., ["body", "email"] -> "body.email")
        field_path = ".".join(str(loc) for loc in error["loc"])

        # Create user-friendly error message
        error_detail = {
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
        }

        # Add additional context for specific error types
        if error.get("ctx"):
            # Convert context to JSON-serializable format
            # Some context values (like ValueError objects) are not serializable
            ctx = error["ctx"]
            serializable_ctx = {}
            for key, value in ctx.items():
                try:
                    # Try to convert to JSON-serializable form
                    import json
                    json.dumps(value)
                    serializable_ctx[key] = value
                except (TypeError, ValueError):
                    # If not serializable, convert to string
                    serializable_ctx[key] = str(value)
            error_detail["context"] = serializable_ctx

        errors.append(error_detail)

    # Log validation errors (info level - these are client errors)
    logger.info(
        f"Validation error in {request.method} {request.url.path}: {len(errors)} field(s) invalid",
        extra={
            "method": request.method,
            "path": request.url.path,
            "validation_errors": errors,
            "client": request.client.host if request.client else None,
        },
    )

    return create_error_response(
        code="validation_error",
        message="Request validation failed. Please check the provided data.",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"fields": errors},
    )


# Additional specialized error handlers


class DatabaseError(Exception):
    """Exception raised for database operation failures."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please try again later.",
        retry_after: int | None = None,
    ):
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)


class PaymentError(Exception):
    """Exception raised for payment processing failures."""

    def __init__(self, message: str, payment_details: Dict[str, Any] | None = None):
        self.message = message
        self.payment_details = payment_details or {}
        super().__init__(self.message)


async def database_exception_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    """
    Handler for database-related errors.

    Args:
        request: FastAPI request object
        exc: DatabaseError instance

    Returns:
        JSONResponse: Database error response (500 Internal Server Error)
    """
    logger.error(
        f"Database error in {request.method} {request.url.path}: {exc.message}",
        exc_info=True,
        extra={"details": exc.details},
    )

    sentry_sdk.capture_exception(exc)

    return create_error_response(
        code="database_error",
        message="A database error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitError) -> JSONResponse:
    """
    Handler for rate limit errors.

    Args:
        request: FastAPI request object
        exc: RateLimitError instance

    Returns:
        JSONResponse: Rate limit error response (429 Too Many Requests)
    """
    logger.warning(
        f"Rate limit exceeded for {request.client.host if request.client else 'unknown'} "
        f"on {request.method} {request.url.path}",
    )

    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)

    response = create_error_response(
        code="rate_limit_exceeded",
        message=exc.message,
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        details={"retry_after": exc.retry_after} if exc.retry_after else None,
    )

    # Add Retry-After header
    for key, value in headers.items():
        response.headers[key] = value

    return response


async def payment_exception_handler(request: Request, exc: PaymentError) -> JSONResponse:
    """
    Handler for payment processing errors.

    Args:
        request: FastAPI request object
        exc: PaymentError instance

    Returns:
        JSONResponse: Payment error response (402 Payment Required or 500 Internal Server Error)
    """
    logger.error(
        f"Payment error in {request.method} {request.url.path}: {exc.message}",
        exc_info=True,
        extra={"payment_details": exc.payment_details},
    )

    sentry_sdk.capture_exception(exc)

    return create_error_response(
        code="payment_error",
        message=exc.message,
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
    )
