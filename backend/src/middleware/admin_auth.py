"""
Admin Authentication Middleware

Provides authentication and authorization for admin-only endpoints via:
1. API key validation (X-API-Key header)
2. IP whitelist check (configurable via ADMIN_IP_WHITELIST env var)

Security Controls:
- API key must match ADMIN_API_KEY environment variable (min 32 chars)
- Request IP must be in ADMIN_IP_WHITELIST (comma-separated IPs)
- Returns 401 Unauthorized for invalid API key
- Returns 403 Forbidden for non-whitelisted IP
- Logs all admin access attempts (successful and failed) for audit trail

Usage:
    from fastapi import Depends
    from src.middleware.admin_auth import require_admin_auth

    @app.get("/admin/something")
    async def admin_endpoint(admin_user: dict = Depends(require_admin_auth)):
        # admin_user contains {"ip": "...", "authenticated_at": "..."}
        return {"data": "sensitive admin data"}

Functional Requirement: FR-M-005 (Admin dashboard authentication)
Reference: tasks.md T127G
"""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import Request, HTTPException, status, Depends, Header
from fastapi.security import APIKeyHeader

from src.lib.env import settings

logger = logging.getLogger(__name__)

# API Key header scheme for OpenAPI documentation
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_admin_auth(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
) -> dict:
    """
    Dependency for admin authentication.

    Validates:
    1. X-API-Key header matches ADMIN_API_KEY environment variable
    2. Request IP is in ADMIN_IP_WHITELIST

    Args:
        request: FastAPI request object (for IP address extraction)
        x_api_key: API key from X-API-Key header

    Returns:
        dict: Admin user context with IP and authentication timestamp

    Raises:
        HTTPException: 401 for invalid API key, 403 for non-whitelisted IP

    Example:
        @app.get("/admin/dashboard")
        async def dashboard(admin: dict = Depends(require_admin_auth)):
            return {"message": f"Admin authenticated from {admin['ip']}"}
    """
    # Extract client IP address
    client_ip = request.client.host if request.client else None

    # Log authentication attempt
    logger.info(
        f"Admin authentication attempt from IP: {client_ip}",
        extra={
            "ip": client_ip,
            "path": request.url.path,
            "method": request.method,
            "has_api_key": bool(x_api_key),
        }
    )

    # Validate API key presence
    if not x_api_key:
        logger.warning(
            f"Admin authentication failed: Missing API key from IP {client_ip}",
            extra={"ip": client_ip, "path": request.url.path}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Admin authentication required. Provide X-API-Key header.",
                "code": "missing_admin_api_key"
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate API key value
    if x_api_key != settings.admin_api_key:
        logger.warning(
            f"Admin authentication failed: Invalid API key from IP {client_ip}",
            extra={
                "ip": client_ip,
                "path": request.url.path,
                "provided_key_length": len(x_api_key),
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Invalid admin API key.",
                "code": "invalid_admin_api_key"
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate IP whitelist
    allowed_ips = settings.admin_ips
    if client_ip not in allowed_ips:
        logger.warning(
            f"Admin authentication failed: IP {client_ip} not in whitelist",
            extra={
                "ip": client_ip,
                "path": request.url.path,
                "allowed_ips": allowed_ips,
            }
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": f"Access forbidden. IP address {client_ip} not in admin whitelist.",
                "code": "ip_not_whitelisted"
            }
        )

    # Authentication successful
    logger.info(
        f"Admin authenticated successfully from IP {client_ip}",
        extra={
            "ip": client_ip,
            "path": request.url.path,
            "method": request.method,
        }
    )

    # Return admin user context
    return {
        "ip": client_ip,
        "authenticated_at": datetime.utcnow().isoformat(),
    }


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.

    Handles X-Forwarded-For header for proxied requests (e.g., behind load balancer).

    Args:
        request: FastAPI request object

    Returns:
        str: Client IP address
    """
    # Check for X-Forwarded-For header (common in proxied environments)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2)
        # First IP is the original client
        return forwarded_for.split(",")[0].strip()

    # Check for X-Real-IP header (alternative proxy header)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct connection IP
    return request.client.host if request.client else "unknown"
