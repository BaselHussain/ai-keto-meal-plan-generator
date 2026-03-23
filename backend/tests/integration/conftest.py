"""
Integration test configuration and fixtures.

Provides shared fixtures for integration tests.
"""

import pytest
from contextlib import asynccontextmanager
from unittest.mock import patch


@pytest.fixture
def patch_get_db_context(test_session):
    """
    Patch get_db_context in service modules to use the test session.

    Service functions (e.g., increment_refund_count) call get_db_context()
    which requires init_db() to have been called at application startup.
    In tests that invoke services directly (not via HTTP), init_db() is
    never called, so we redirect get_db_context to yield the test session.

    Use this fixture explicitly in tests that call service functions directly:

        async def test_something(test_session, patch_get_db_context):
            await increment_refund_count("some@example.com")
    """
    @asynccontextmanager
    async def _mock_get_db_context():
        yield test_session

    with patch(
        "src.services.refund_count_service.get_db_context",
        side_effect=_mock_get_db_context,
    ):
        yield
