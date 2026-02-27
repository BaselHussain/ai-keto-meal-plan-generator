"""
Unit tests for admin dashboard endpoints.

Tests:
- GET /admin/manual-resolution (list entries)
- POST /admin/manual-resolution/{id}/resolve (mark as resolved)
- POST /admin/manual-resolution/{id}/regenerate (trigger PDF regeneration)
- POST /admin/manual-resolution/{id}/refund (issue refund)

Reference: tasks.md T127H-T127J
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from src.main import app
from src.models.manual_resolution import ManualResolution

# The API key used throughout this test module.
TEST_ADMIN_API_KEY = "test_admin_key_with_sufficient_length_32chars"


@pytest.fixture(autouse=True)
def patch_admin_settings():
    """
    Patch the settings object used by admin_auth middleware so that the
    test API key and a permissive IP whitelist are active for every test
    in this module.  TestClient uses 'testclient' as the client IP, so we
    add it to the whitelist.
    """
    with patch("src.middleware.admin_auth.settings") as mock_settings:
        mock_settings.admin_api_key = TEST_ADMIN_API_KEY
        mock_settings.admin_ips = ["127.0.0.1", "::1", "testclient"]
        yield mock_settings


@pytest.fixture
def mock_db():
    """
    Provide a mock database session that works with the admin API's synchronous
    call patterns (``db.execute(...).scalar()``, ``db.execute(...).scalar_one_or_none()``).

    The admin API was written with synchronous SQLAlchemy Session patterns.
    We use a plain ``MagicMock`` (not ``AsyncMock``) so the returned values
    from ``execute()`` are regular mocks whose attributes (``.scalar()``,
    ``.scalar_one_or_none()``, ``.scalars().all()``) are callable without
    ``await``.

    We override ``get_db`` via ``app.dependency_overrides`` so that FastAPI's
    dependency injection system injects this mock instead of calling the real
    database.
    """
    from src.lib.database import get_db

    db = MagicMock()

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    yield db
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(mock_db):
    """Create a test client with the get_db dependency overridden."""
    return TestClient(app)


@pytest.fixture
def admin_headers():
    """Admin authentication headers."""
    return {
        "X-API-Key": TEST_ADMIN_API_KEY
    }


@pytest.fixture
def mock_manual_resolution_entries():
    """Create mock manual resolution entries."""
    now = datetime.utcnow()
    entries = []

    for i in range(5):
        entry = ManualResolution(
            id=str(uuid4()),
            payment_id=f"txn_test_{i}",
            user_email=f"user{i}@example.com",
            normalized_email=f"user{i}@example.com",
            issue_type="ai_validation_failed",
            status="pending" if i < 3 else "resolved",
            sla_deadline=now + timedelta(hours=4 - i),  # Different SLA deadlines
            created_at=now - timedelta(hours=i),
            resolved_at=now if i >= 3 else None,
            assigned_to=None,
            resolution_notes=None,
        )
        entries.append(entry)

    return entries


@pytest.mark.asyncio
async def test_list_manual_resolution_entries_success(
    client, admin_headers, mock_db, mock_manual_resolution_entries
):
    """Test successful listing of manual resolution entries."""
    # Mock query results
    mock_db.execute.return_value.scalars.return_value.all.return_value = (
        mock_manual_resolution_entries
    )
    mock_db.execute.return_value.scalar.return_value = len(mock_manual_resolution_entries)

    response = client.get("/api/v1/admin/manual-resolution", headers=admin_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "entries" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert "pending_count" in data
    assert "sla_breached_count" in data

    assert isinstance(data["entries"], list)


@pytest.mark.asyncio
async def test_list_manual_resolution_entries_unauthorized(client):
    """Test listing without API key."""
    response = client.get("/api/v1/admin/manual-resolution")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_list_manual_resolution_entries_invalid_api_key(client):
    """Test listing with invalid API key."""
    response = client.get(
        "/api/v1/admin/manual-resolution",
        headers={"X-API-Key": "invalid_key"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_list_manual_resolution_entries_with_status_filter(client, admin_headers, mock_db):
    """Test listing with status filter."""
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    mock_db.execute.return_value.scalar.return_value = 0

    response = client.get(
        "/api/v1/admin/manual-resolution?status_filter=pending",
        headers=admin_headers
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_list_manual_resolution_entries_with_sorting(client, admin_headers, mock_db):
    """Test listing with sorting."""
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    mock_db.execute.return_value.scalar.return_value = 0

    response = client.get(
        "/api/v1/admin/manual-resolution?sort_by=priority&sort_order=asc",
        headers=admin_headers
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_resolve_manual_resolution_entry_success(
    client, admin_headers, mock_db, mock_manual_resolution_entries
):
    """Test successfully resolving a manual resolution entry."""
    entry = mock_manual_resolution_entries[0]

    # Mock query result
    mock_db.execute.return_value.scalar_one_or_none.return_value = entry

    response = client.post(
        f"/api/v1/admin/manual-resolution/{entry.id}/resolve",
        headers=admin_headers,
        json={
            "assigned_to": "admin@ketomealplan.com",
            "resolution_notes": "Manually regenerated PDF and sent email"
        }
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["success"] is True
    assert data["entry_id"] == entry.id
    assert data["updated_status"] == "resolved"


@pytest.mark.asyncio
async def test_resolve_manual_resolution_entry_not_found(client, admin_headers, mock_db):
    """Test resolving non-existent entry."""
    # Mock not found
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    response = client.post(
        f"/api/v1/admin/manual-resolution/{uuid4()}/resolve",
        headers=admin_headers,
        json={
            "resolution_notes": "Test notes"
        }
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_resolve_manual_resolution_entry_unauthorized(client):
    """Test resolving without API key."""
    response = client.post(
        f"/api/v1/admin/manual-resolution/{uuid4()}/resolve",
        json={
            "resolution_notes": "Test notes"
        }
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_regenerate_pdf_success(client, admin_headers, mock_db, mock_manual_resolution_entries):
    """Test successfully triggering PDF regeneration."""
    entry = mock_manual_resolution_entries[0]

    mock_db.execute.return_value.scalar_one_or_none.return_value = entry

    response = client.post(
        f"/api/v1/admin/manual-resolution/{entry.id}/regenerate",
        headers=admin_headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["success"] is True
    assert data["entry_id"] == entry.id
    assert data["updated_status"] == "in_progress"


@pytest.mark.asyncio
async def test_regenerate_pdf_not_found(client, admin_headers, mock_db):
    """Test regenerating PDF for non-existent entry."""
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    response = client.post(
        f"/api/v1/admin/manual-resolution/{uuid4()}/regenerate",
        headers=admin_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_refund_success(client, admin_headers, mock_db, mock_manual_resolution_entries):
    """Test successfully issuing refund."""
    entry = mock_manual_resolution_entries[0]

    mock_db.execute.return_value.scalar_one_or_none.return_value = entry

    response = client.post(
        f"/api/v1/admin/manual-resolution/{entry.id}/refund",
        headers=admin_headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["success"] is True
    assert data["entry_id"] == entry.id
    assert data["updated_status"] == "sla_missed_refunded"


@pytest.mark.asyncio
async def test_refund_not_found(client, admin_headers, mock_db):
    """Test refunding non-existent entry."""
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    response = client.post(
        f"/api/v1/admin/manual-resolution/{uuid4()}/refund",
        headers=admin_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_refund_unauthorized(client):
    """Test refunding without API key."""
    response = client.post(
        f"/api/v1/admin/manual-resolution/{uuid4()}/refund"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
