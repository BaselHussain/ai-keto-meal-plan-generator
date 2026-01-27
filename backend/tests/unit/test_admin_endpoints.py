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
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.models.manual_resolution import ManualResolution


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def admin_headers():
    """Admin authentication headers."""
    return {
        "X-API-Key": "test_admin_key_with_sufficient_length_32chars"
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
    client, admin_headers, mock_manual_resolution_entries
):
    """Test successful listing of manual resolution entries."""
    with patch("src.api.admin.get_db") as mock_get_db:
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db

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
async def test_list_manual_resolution_entries_with_status_filter(client, admin_headers):
    """Test listing with status filter."""
    with patch("src.api.admin.get_db") as mock_get_db:
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db

        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        mock_db.execute.return_value.scalar.return_value = 0

        response = client.get(
            "/api/v1/admin/manual-resolution?status_filter=pending",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_list_manual_resolution_entries_with_sorting(client, admin_headers):
    """Test listing with sorting."""
    with patch("src.api.admin.get_db") as mock_get_db:
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db

        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        mock_db.execute.return_value.scalar.return_value = 0

        response = client.get(
            "/api/v1/admin/manual-resolution?sort_by=priority&sort_order=asc",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_resolve_manual_resolution_entry_success(
    client, admin_headers, mock_manual_resolution_entries
):
    """Test successfully resolving a manual resolution entry."""
    entry = mock_manual_resolution_entries[0]

    with patch("src.api.admin.get_db") as mock_get_db:
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db

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
async def test_resolve_manual_resolution_entry_not_found(client, admin_headers):
    """Test resolving non-existent entry."""
    with patch("src.api.admin.get_db") as mock_get_db:
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db

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
async def test_regenerate_pdf_success(client, admin_headers, mock_manual_resolution_entries):
    """Test successfully triggering PDF regeneration."""
    entry = mock_manual_resolution_entries[0]

    with patch("src.api.admin.get_db") as mock_get_db:
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db

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
async def test_regenerate_pdf_not_found(client, admin_headers):
    """Test regenerating PDF for non-existent entry."""
    with patch("src.api.admin.get_db") as mock_get_db:
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db

        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        response = client.post(
            f"/api/v1/admin/manual-resolution/{uuid4()}/regenerate",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_refund_success(client, admin_headers, mock_manual_resolution_entries):
    """Test successfully issuing refund."""
    entry = mock_manual_resolution_entries[0]

    with patch("src.api.admin.get_db") as mock_get_db:
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db

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
async def test_refund_not_found(client, admin_headers):
    """Test refunding non-existent entry."""
    with patch("src.api.admin.get_db") as mock_get_db:
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db

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
