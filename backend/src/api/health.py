"""
Health Check Endpoint

Provides comprehensive health status monitoring for the application.
Used by load balancers, monitoring tools, and orchestration platforms
to determine service availability.

Endpoints:
- GET /health - Simple health check (returns 200 if service is running)
- GET /health/detailed - Detailed health check with component status

Health Check Strategy:
- Quick response time (< 100ms target)
- Checks critical dependencies (database, cache)
- Returns appropriate HTTP status codes
- Minimal resource usage
- No authentication required
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.lib.database import health_check as db_health_check
from src.lib.env import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    response_model=None,
    summary="Simple health check",
    description="Returns 200 OK if the service is running. Used by load balancers and monitoring tools.",
)
async def health_check() -> Dict[str, str]:
    """
    Simple health check endpoint.

    Returns a basic health status without checking dependencies.
    This is the fastest health check and should be used for:
    - Load balancer health checks
    - Container orchestration (Kubernetes liveness probes)
    - High-frequency monitoring

    Returns:
        dict: Basic health status
            - status: Always "healthy" if service is responding
    """
    return {"status": "healthy"}


@router.get(
    "/health/detailed",
    status_code=status.HTTP_200_OK,
    response_model=None,
    summary="Detailed health check",
    description="Returns detailed health status including database and cache connectivity.",
)
async def detailed_health_check() -> JSONResponse:
    """
    Detailed health check endpoint.

    Checks the health of all critical application components:
    - API service (always healthy if responding)
    - Database connectivity and pool status
    - Redis cache connectivity (future)
    - External service availability (future)

    Returns:
        JSONResponse: Comprehensive health status
            - status: "healthy" if all components are operational, "degraded" or "unhealthy" otherwise
            - service: Service name
            - environment: Current environment (development/staging/production)
            - components: Dict of component health statuses

    HTTP Status Codes:
        - 200: All components healthy
        - 503: One or more critical components unhealthy
    """
    # Check database health
    db_health = await db_health_check()

    # TODO: Add Redis health check when implemented
    # redis_health = await redis_health_check()

    # TODO: Add external service health checks (Paddle, Resend, etc.)

    # Determine overall health status
    components = {
        "api": {"status": "healthy"},
        "database": db_health,
        # "redis": redis_health,  # Uncomment when implemented
    }

    # Overall status is healthy only if all critical components are healthy
    all_healthy = all(
        component.get("status") == "healthy"
        for component in components.values()
    )

    overall_status = "healthy" if all_healthy else "unhealthy"

    response_data = {
        "status": overall_status,
        "service": "keto-meal-plan-api",
        "environment": settings.env,
        "components": components,
    }

    # Return 503 Service Unavailable if any component is unhealthy
    status_code = (
        status.HTTP_200_OK if all_healthy
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        status_code=status_code,
        content=response_data,
    )


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    response_model=None,
    summary="Readiness check",
    description="Returns 200 OK when the service is ready to accept traffic.",
)
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check endpoint.

    Used by Kubernetes and other orchestration platforms to determine
    if the service is ready to receive traffic. Unlike liveness checks,
    readiness checks verify that all dependencies are available.

    A service can be alive but not ready (e.g., database is still connecting).

    Returns:
        dict: Readiness status
            - ready: True if service is ready to accept traffic
            - status: "ready" or "not_ready"

    HTTP Status Codes:
        - 200: Service is ready
        - 503: Service is not ready (still initializing)
    """
    # Check if critical dependencies are available
    db_health = await db_health_check()

    is_ready = db_health.get("status") == "healthy"

    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "ready": False,
                "status": "not_ready",
                "reason": "Database not available",
            },
        )

    return {
        "ready": True,
        "status": "ready",
    }
