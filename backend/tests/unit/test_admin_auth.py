"""
Unit tests for admin authentication middleware.

Tests:
- API key validation
- IP whitelist check
- Authentication success/failure scenarios
- Error handling

Reference: tasks.md T127G
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException, Request
from datetime import datetime

from src.middleware.admin_auth import require_admin_auth, get_client_ip


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request object."""
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "127.0.0.1"
    request.url = Mock()
    request.url.path = "/admin/test"
    request.method = "GET"
    request.headers = {}
    return request


@pytest.fixture
def mock_settings():
    """Mock settings with admin configuration."""
    with patch("src.middleware.admin_auth.settings") as mock:
        mock.admin_api_key = "test_admin_key_with_sufficient_length_32chars"
        mock.admin_ips = ["127.0.0.1", "::1", "192.168.1.100"]
        yield mock


@pytest.mark.asyncio
async def test_require_admin_auth_success(mock_request, mock_settings):
    """Test successful admin authentication."""
    # Valid API key and whitelisted IP
    result = await require_admin_auth(
        request=mock_request,
        x_api_key="test_admin_key_with_sufficient_length_32chars"
    )

    assert result["ip"] == "127.0.0.1"
    assert "authenticated_at" in result
    assert isinstance(result["authenticated_at"], str)


@pytest.mark.asyncio
async def test_require_admin_auth_missing_api_key(mock_request, mock_settings):
    """Test authentication failure with missing API key."""
    with pytest.raises(HTTPException) as exc_info:
        await require_admin_auth(request=mock_request, x_api_key=None)

    assert exc_info.value.status_code == 401
    assert "missing_admin_api_key" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_require_admin_auth_invalid_api_key(mock_request, mock_settings):
    """Test authentication failure with invalid API key."""
    with pytest.raises(HTTPException) as exc_info:
        await require_admin_auth(request=mock_request, x_api_key="invalid_key")

    assert exc_info.value.status_code == 401
    assert "invalid_admin_api_key" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_require_admin_auth_ip_not_whitelisted(mock_request, mock_settings):
    """Test authentication failure with non-whitelisted IP."""
    # Valid API key but non-whitelisted IP
    mock_request.client.host = "203.0.113.5"  # Not in whitelist

    with pytest.raises(HTTPException) as exc_info:
        await require_admin_auth(
            request=mock_request,
            x_api_key="test_admin_key_with_sufficient_length_32chars"
        )

    assert exc_info.value.status_code == 403
    assert "ip_not_whitelisted" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_require_admin_auth_ipv6_localhost(mock_request, mock_settings):
    """Test authentication with IPv6 localhost."""
    mock_request.client.host = "::1"

    result = await require_admin_auth(
        request=mock_request,
        x_api_key="test_admin_key_with_sufficient_length_32chars"
    )

    assert result["ip"] == "::1"
    assert "authenticated_at" in result


@pytest.mark.asyncio
async def test_require_admin_auth_whitelisted_ip(mock_request, mock_settings):
    """Test authentication with whitelisted IP."""
    mock_request.client.host = "192.168.1.100"

    result = await require_admin_auth(
        request=mock_request,
        x_api_key="test_admin_key_with_sufficient_length_32chars"
    )

    assert result["ip"] == "192.168.1.100"


def test_get_client_ip_direct_connection(mock_request):
    """Test extracting IP from direct connection."""
    ip = get_client_ip(mock_request)
    assert ip == "127.0.0.1"


def test_get_client_ip_x_forwarded_for(mock_request):
    """Test extracting IP from X-Forwarded-For header (proxy)."""
    headers_mock = Mock()
    headers_mock.get = Mock(
        side_effect=lambda key: "203.0.113.5, 198.51.100.10" if key == "X-Forwarded-For" else None
    )
    mock_request.headers = headers_mock

    ip = get_client_ip(mock_request)
    assert ip == "203.0.113.5"  # First IP in chain


def test_get_client_ip_x_real_ip(mock_request):
    """Test extracting IP from X-Real-IP header."""
    headers_mock = Mock()
    headers_mock.get = Mock(
        side_effect=lambda key: "203.0.113.5" if key == "X-Real-IP" else None
    )
    mock_request.headers = headers_mock

    ip = get_client_ip(mock_request)
    assert ip == "203.0.113.5"


def test_get_client_ip_no_client(mock_request):
    """Test extracting IP when client is None."""
    mock_request.client = None
    ip = get_client_ip(mock_request)
    assert ip == "unknown"


@pytest.mark.asyncio
async def test_require_admin_auth_no_client(mock_settings):
    """Test authentication when request.client is None."""
    request = Mock(spec=Request)
    request.client = None
    request.url = Mock()
    request.url.path = "/admin/test"
    request.method = "GET"

    with pytest.raises(HTTPException) as exc_info:
        await require_admin_auth(
            request=request,
            x_api_key="test_admin_key_with_sufficient_length_32chars"
        )

    # Should fail IP whitelist check (None not in whitelist)
    assert exc_info.value.status_code == 403
