"""
FastAPI Middleware

Custom middleware for request/response processing, error handling,
rate limiting, authentication, and logging.

Middleware Execution Order (top to bottom):
1. CORS (built-in FastAPI middleware)
2. Sentry Context (in main.py)
3. Error Handler (exception handlers in main.py)
4. Rate Limiting (future)
5. Authentication (future)
6. Request Logging (future)
7. Route Handlers

Available Middleware:
- error_handler: Global exception handling with structured error responses
- rate_limit: Rate limiting middleware (future)
- auth: Authentication and authorization middleware (future)
"""

from src.middleware.error_handler import (
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)

__all__ = [
    "global_exception_handler",
    "http_exception_handler",
    "validation_exception_handler",
]
