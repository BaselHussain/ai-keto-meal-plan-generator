"""
FastAPI Application Entry Point

Production-ready FastAPI application with:
- Comprehensive error handling and structured error responses
- Sentry integration for error tracking
- CORS configuration for frontend integration
- Health check endpoint for monitoring
- Modular router structure
- Async request handling
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from dotenv import load_dotenv

# Load environment variables FIRST before importing modules that read them
load_dotenv()

# Import database utilities
from src.lib.database import init_db, close_db
from src.lib.env import settings

# Import middleware
from src.middleware.error_handler import (
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)

# Import API routers
from src.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.env == "production" else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def filter_sentry_events(event, hint):
    """
    Filter out health check and monitoring endpoints from Sentry.
    Reduces noise and focuses on actual application errors.

    Args:
        event: Sentry event dict
        hint: Additional context about the event

    Returns:
        Filtered event or None to drop the event
    """
    # Skip health checks and monitoring endpoints
    if event.get("transaction") in ["/health", "/", "/metrics", "/docs", "/redoc", "/openapi.json"]:
        return None

    # Skip successful health check requests
    if "request" in event:
        url = event["request"].get("url", "")
        if any(endpoint in url for endpoint in ["/health", "/metrics"]):
            return None

    return event


# Initialize Sentry with comprehensive monitoring
if settings.sentry_backend_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_backend_dsn,
        environment=settings.env,

        # Integrations for FastAPI, database, cache, and logging
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint",  # Use endpoint names for transaction names
                failed_request_status_codes=[400, range(500, 599)],  # Track 4xx and 5xx errors
            ),
            SqlalchemyIntegration(),  # Track database queries and errors
            RedisIntegration(),  # Track Redis operations
            LoggingIntegration(
                level=logging.INFO,  # Capture INFO level logs as breadcrumbs
                event_level=logging.ERROR,  # Send ERROR level logs as events
            ),
        ],

        # Performance monitoring - sample more in development, less in production
        traces_sample_rate=1.0 if settings.env == "development" else 0.1,  # 100% dev, 10% prod
        profiles_sample_rate=1.0 if settings.env == "development" else 0.1,  # 100% dev, 10% prod
        enable_tracing=True,

        # Release tracking for better error tracking across deployments
        release=settings.sentry_release or "keto-meal-plan-api@1.0.0",

        # Filter out noise from health checks
        before_send=filter_sentry_events,

        # Enable sending user PII for better debugging (GDPR compliant if documented)
        send_default_pii=True,

        # Additional settings
        attach_stacktrace=True,  # Include stack traces in messages
        max_breadcrumbs=50,  # Keep last 50 breadcrumbs for context
    )
    logger.info("Sentry initialized successfully")
else:
    logger.warning("Sentry DSN not configured - error tracking disabled")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifecycle manager.

    Handles startup and shutdown events:
    - Startup: Initialize database, Redis, and other resources
    - Shutdown: Clean up connections and resources

    Args:
        app: FastAPI application instance

    Yields:
        None during application runtime
    """
    # Startup
    logger.info("Starting application initialization...")

    try:
        # Initialize database connection
        init_db()
        logger.info("✓ Database connection initialized")

        # Add other initialization here (Redis, background tasks, etc.)
        # TODO: Initialize Redis client when implemented
        # TODO: Start background task workers when implemented

        logger.info("✓ Application startup complete")

    except Exception as e:
        logger.error(f"✗ Failed to initialize application: {str(e)}", exc_info=True)
        raise

    # Application running
    yield

    # Shutdown
    logger.info("Starting application shutdown...")

    try:
        # Close database connections
        await close_db()
        logger.info("✓ Database connections closed")

        # Add other cleanup here (Redis, background tasks, etc.)
        # TODO: Close Redis connections when implemented
        # TODO: Cancel background tasks when implemented

        logger.info("✓ Application shutdown complete")

    except Exception as e:
        logger.error(f"✗ Error during shutdown: {str(e)}", exc_info=True)


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Keto Meal Plan Generator API",
    description="AI-powered personalized keto meal plan generation service",
    version="1.0.0",
    docs_url="/docs" if settings.env != "production" else None,  # Disable docs in production
    redoc_url="/redoc" if settings.env != "production" else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        settings.app_url,  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Sentry context middleware
@app.middleware("http")
async def add_sentry_context(request: Request, call_next):
    """
    Add contextual information to Sentry events.
    This helps with debugging by providing request details and user information.

    Args:
        request: FastAPI request object
        call_next: Next middleware/handler in chain

    Returns:
        Response from the next handler
    """
    # Add request context
    with sentry_sdk.configure_scope() as scope:
        # Add custom tags for filtering in Sentry
        scope.set_tag("endpoint", request.url.path)
        scope.set_tag("method", request.method)
        scope.set_tag("host", request.client.host if request.client else "unknown")

        # Add request details as context
        scope.set_context("request_details", {
            "url": str(request.url),
            "method": request.method,
            "headers": dict(request.headers),
            "query_params": dict(request.query_params),
        })

        # Add user context if available (will be populated later with auth)
        # For now, we'll use IP as identifier for anonymous users
        if request.client:
            scope.set_user({
                "ip_address": request.client.host,
            })

        # Note: When JWT authentication is implemented, update this to:
        # if hasattr(request.state, "user") and request.state.user:
        #     scope.set_user({
        #         "id": request.state.user.id,
        #         "email": request.state.user.email,
        #         "ip_address": request.client.host if request.client else None,
        #     })

    response = await call_next(request)

    # Add response status to breadcrumbs
    sentry_sdk.add_breadcrumb(
        category="http.response",
        message=f"{request.method} {request.url.path} - {response.status_code}",
        level="info",
    )

    return response


# Register exception handlers
app.add_exception_handler(Exception, global_exception_handler)
from fastapi.exceptions import HTTPException, RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


# Include API routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """
    Root endpoint.

    Returns basic API information and status.

    Returns:
        dict: API metadata and status
    """
    return {
        "message": "Keto Meal Plan Generator API",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs" if settings.env != "production" else None,
    }


@app.get("/sentry-debug")
async def trigger_sentry_error():
    """
    Test endpoint to trigger a Sentry error.

    Only available in non-production environments for testing error tracking.

    Raises:
        ZeroDivisionError: Always raised for testing purposes
    """
    if settings.env == "production":
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "not_found", "message": "Endpoint not found"}},
        )

    division_by_zero = 1 / 0  # This will trigger an error
    return {"message": "This will never be returned"}
