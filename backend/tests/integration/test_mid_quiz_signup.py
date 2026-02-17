"""
Integration tests for mid-quiz signup progress saving and loading (T127A).

Tests:
1. POST /quiz/save-progress with valid JWT saves quiz data
2. POST /quiz/save-progress without JWT returns 401
3. GET /quiz/load-progress returns last saved step
4. GET /quiz/load-progress with no saved data returns 404
5. Save progress updates existing record (no duplicates)
6. Cross-device: save on device A, load on device B with same account
"""

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth_service import create_access_token
from src.models.quiz_response import QuizResponse


# --- Fixtures ---

@pytest.fixture
def test_user_id():
    return str(uuid.uuid4())


@pytest.fixture
def test_user_email():
    return "quizuser@example.com"


@pytest.fixture
def valid_jwt(test_user_id, test_user_email):
    return create_access_token(user_id=test_user_id, email=test_user_email)


@pytest.fixture
def auth_headers(valid_jwt):
    return {"Authorization": f"Bearer {valid_jwt}"}


@pytest.fixture
def partial_quiz_data():
    return {
        "step_1": "female",
        "step_2": "moderately_active",
        "step_3": ["chicken", "turkey"],
        "step_4": ["salmon"],
        "step_5": [],
        "step_6": [],
        "step_7": [],
    }


@pytest.fixture
def extended_quiz_data(partial_quiz_data):
    return {
        **partial_quiz_data,
        "step_8": ["zucchini"],
        "step_9": ["eggs"],
        "step_10": [],
        "step_11": ["blueberries"],
        "step_12": ["almonds", "walnuts"],
    }


# --- Tests ---

@pytest.mark.asyncio
async def test_save_progress_with_valid_jwt(async_client: AsyncClient, auth_headers, partial_quiz_data, test_session: AsyncSession):
    """T127A-1: POST /quiz/save-progress with valid JWT saves quiz data to database."""
    response = await async_client.post(
        "/api/v1/quiz/save-progress",
        json={"current_step": 7, "quiz_data": partial_quiz_data},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["current_step"] == 7
    assert "saved_at" in data


@pytest.mark.asyncio
async def test_save_progress_without_jwt(async_client: AsyncClient, partial_quiz_data):
    """T127A-2: POST /quiz/save-progress without JWT returns 401."""
    response = await async_client.post(
        "/api/v1/quiz/save-progress",
        json={"current_step": 3, "quiz_data": partial_quiz_data},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_save_progress_invalid_jwt(async_client: AsyncClient, partial_quiz_data):
    """T127A-2b: POST /quiz/save-progress with invalid JWT returns 401."""
    response = await async_client.post(
        "/api/v1/quiz/save-progress",
        json={"current_step": 3, "quiz_data": partial_quiz_data},
        headers={"Authorization": "Bearer invalid-token-here"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_load_progress_returns_saved_step(async_client: AsyncClient, auth_headers, partial_quiz_data):
    """T127A-3: GET /quiz/load-progress returns last saved step data."""
    # Save progress first
    await async_client.post(
        "/api/v1/quiz/save-progress",
        json={"current_step": 7, "quiz_data": partial_quiz_data},
        headers=auth_headers,
    )

    # Load progress
    response = await async_client.get(
        "/api/v1/quiz/load-progress",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["quiz_data"]["step_1"] == "female"
    assert data["quiz_data"]["step_2"] == "moderately_active"
    assert "saved_at" in data


@pytest.mark.asyncio
async def test_load_progress_no_saved_data(async_client: AsyncClient):
    """T127A-4: GET /quiz/load-progress with no saved data returns 404."""
    # Create a fresh user with no saved progress
    fresh_user_id = str(uuid.uuid4())
    fresh_jwt = create_access_token(user_id=fresh_user_id, email="fresh@example.com")

    response = await async_client.get(
        "/api/v1/quiz/load-progress",
        headers={"Authorization": f"Bearer {fresh_jwt}"},
    )
    assert response.status_code == 404
    assert "No saved quiz progress" in response.json()["detail"]


@pytest.mark.asyncio
async def test_save_progress_updates_existing_record(async_client: AsyncClient, auth_headers, partial_quiz_data, extended_quiz_data, test_session: AsyncSession, test_user_id):
    """T127A-5: Save progress updates existing record, no duplicates."""
    # First save
    await async_client.post(
        "/api/v1/quiz/save-progress",
        json={"current_step": 5, "quiz_data": partial_quiz_data},
        headers=auth_headers,
    )

    # Second save (update)
    await async_client.post(
        "/api/v1/quiz/save-progress",
        json={"current_step": 12, "quiz_data": extended_quiz_data},
        headers=auth_headers,
    )

    # Verify only one in-progress record exists for this user
    result = await test_session.execute(
        select(func.count()).select_from(QuizResponse).where(
            QuizResponse.user_id == test_user_id,
            QuizResponse.payment_id == None,
        )
    )
    count = result.scalar()
    assert count == 1

    # Verify data is from the second save
    load_response = await async_client.get(
        "/api/v1/quiz/load-progress",
        headers=auth_headers,
    )
    assert load_response.status_code == 200
    loaded_data = load_response.json()["quiz_data"]
    assert "step_12" in loaded_data


@pytest.mark.asyncio
async def test_cross_device_progress_sync(async_client: AsyncClient, test_user_id, test_user_email, partial_quiz_data):
    """T127A-6: Cross-device - save on device A, load on device B with same account."""
    # Both devices use same user credentials -> same JWT
    jwt_device_a = create_access_token(user_id=test_user_id, email=test_user_email)
    jwt_device_b = create_access_token(user_id=test_user_id, email=test_user_email)

    # Device A saves progress
    save_response = await async_client.post(
        "/api/v1/quiz/save-progress",
        json={"current_step": 8, "quiz_data": partial_quiz_data},
        headers={"Authorization": f"Bearer {jwt_device_a}"},
    )
    assert save_response.status_code == 200

    # Device B loads progress
    load_response = await async_client.get(
        "/api/v1/quiz/load-progress",
        headers={"Authorization": f"Bearer {jwt_device_b}"},
    )
    assert load_response.status_code == 200
    data = load_response.json()
    assert data["quiz_data"]["step_1"] == partial_quiz_data["step_1"]
    assert data["quiz_data"]["step_2"] == partial_quiz_data["step_2"]
