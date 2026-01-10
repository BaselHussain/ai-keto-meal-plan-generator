import os
import logging
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from dotenv import load_dotenv

# Import database utilities
from src.lib.database import init_db, close_db, health_check as db_health_check

# Load environment variables
load_dotenv()

# Get environment
ENV = os.getenv("ENV", "development")


def filter_sentry_events(event, hint):
    """
    Filter out health check and monitoring endpoints from Sentry.
    Reduces noise and focuses on actual application errors.
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
sentry_sdk.init(
    dsn=os.getenv("SENTRY_BACKEND_DSN"),
    environment=ENV,

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
    traces_sample_rate=1.0 if ENV == "development" else 0.1,  # 100% dev, 10% prod
    profiles_sample_rate=1.0 if ENV == "development" else 0.1,  # 100% dev, 10% prod
    enable_tracing=True,

    # Release tracking for better error tracking across deployments
    release=os.getenv("SENTRY_RELEASE", "keto-meal-plan-api@1.0.0"),

    # Filter out noise from health checks
    before_send=filter_sentry_events,

    # Enable sending user PII for better debugging (GDPR compliant if documented)
    send_default_pii=True,

    # Additional settings
    attach_stacktrace=True,  # Include stack traces in messages
    max_breadcrumbs=50,  # Keep last 50 breadcrumbs for context
)

# Initialize FastAPI app
app = FastAPI(
    title="Keto Meal Plan Generator API",
    description="AI-powered personalized keto meal plan generation service",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        os.getenv("APP_URL", "http://localhost:3000"),  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Application lifecycle events
@app.on_event("startup")
async def startup():
    """
    Initialize application resources on startup.
    - Database connection pool
    - Redis connection (future)
    - Background task workers (future)
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting application initialization...")

    # Initialize database connection
    try:
        init_db()
        logger.info("Database connection initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        raise

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown():
    """
    Clean up application resources on shutdown.
    - Close database connections
    - Close Redis connections (future)
    - Cancel background tasks (future)
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting application shutdown...")

    # Close database connections
    try:
        await close_db()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database: {str(e)}", exc_info=True)

    logger.info("Application shutdown complete")


# Sentry context middleware
@app.middleware("http")
async def add_sentry_context(request: Request, call_next):
    """
    Add contextual information to Sentry events.
    This helps with debugging by providing request details and user information.
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


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Keto Meal Plan Generator API",
        "status": "online",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint for monitoring.

    Checks:
    - API service availability
    - Database connection status
    - Environment configuration

    Returns:
        dict: Health status with component checks
    """
    # Check database health
    db_health = await db_health_check()

    # Overall health status (healthy only if all components are healthy)
    overall_status = "healthy" if db_health.get("status") == "healthy" else "unhealthy"

    return {
        "status": overall_status,
        "service": "keto-meal-plan-api",
        "environment": os.getenv("ENV", "development"),
        "components": {
            "api": "healthy",
            "database": db_health,
        }
    }


@app.get("/sentry-debug")
async def trigger_error():
    """Test endpoint to trigger a Sentry error (for testing only)"""
    division_by_zero = 1 / 0  # This will trigger an error
    return {"message": "This will never be returned"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
