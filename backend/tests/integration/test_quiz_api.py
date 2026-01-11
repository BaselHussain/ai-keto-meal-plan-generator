"""
Integration tests for /api/quiz/submit endpoint (T040-T042).

Tests cover:
- T040: Quiz submission endpoint functionality
- T041: Calorie calculation integration
- T042: Food item validation (FR-Q-017)

These tests verify the complete request/response cycle including:
- Request validation (Pydantic schemas)
- Email normalization (FR-P-010)
- Calorie calculation (Mifflin-St Jeor)
- Food item count validation (10 minimum)
- Database persistence
- Error handling
"""

import copy
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.lib.database import get_db
from src.models.quiz_response import QuizResponse


# Test client fixture
@pytest_asyncio.fixture
async def client(test_session: AsyncSession):
    """Create async test client for API requests with database override."""
    # Override database dependency to use test session
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    # Create async client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    # Clean up override
    app.dependency_overrides.clear()


# Sample valid quiz data
@pytest.fixture
def valid_quiz_data():
    """Valid quiz data with all required fields.

    Returns a deep copy to prevent test mutations from affecting other tests.
    """
    base_data = {
        "email": "test@example.com",
        "quiz_data": {
            "step_1": "male",
            "step_2": "moderately_active",
            "step_3": ["chicken", "turkey"],  # Poultry
            "step_4": ["salmon", "tuna"],  # Fish
            "step_5": ["broccoli", "spinach"],  # Low-carb vegetables
            "step_6": ["cauliflower"],  # Cruciferous
            "step_7": ["kale"],  # Leafy greens
            "step_8": ["zucchini"],  # Additional vegetables
            "step_9": ["beef", "pork"],  # Additional proteins
            "step_10": [],  # Organ meats (optional)
            "step_11": ["blueberries"],  # Berries
            "step_12": ["almonds"],  # Nuts & seeds
            "step_13": ["garlic", "oregano"],  # Herbs & spices (14 items total)
            "step_14": ["olive_oil"],  # Fats & oils
            "step_15": ["water"],  # Beverages
            "step_16": ["cheese"],  # Dairy
            "step_17": "No shellfish please",  # Dietary restrictions
            "step_18": "3",  # Meals per day
            "step_19": ["meal_prep", "snacking"],  # Behavioral patterns
            "step_20": {
                "age": 30,
                "weight_kg": 75.0,
                "height_cm": 175.0,
                "goal": "weight_loss"
            }
        }
    }
    return copy.deepcopy(base_data)


class TestQuizSubmissionSuccess:
    """Test successful quiz submission scenarios (T040)."""

    @pytest.mark.asyncio
    async def test_submit_valid_quiz(self, client, valid_quiz_data, test_session: AsyncSession):
        """Test successful quiz submission with valid data."""
        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["success"] is True
        assert "quiz_id" in data
        assert "calorie_target" in data
        assert data["message"] == "Quiz submitted successfully"
        assert isinstance(data["quiz_id"], str)
        assert isinstance(data["calorie_target"], int)

        # Verify database persistence
        quiz_id = data["quiz_id"]
        stmt = select(QuizResponse).where(QuizResponse.id == quiz_id)
        result = await test_session.execute(stmt)
        quiz_response = result.scalar_one_or_none()

        assert quiz_response is not None
        assert quiz_response.email == "test@example.com"
        assert quiz_response.normalized_email == "test@example.com"  # No normalization needed
        assert quiz_response.calorie_target == data["calorie_target"]
        assert quiz_response.quiz_data["step_1"] == "male"
        assert quiz_response.payment_id is None  # Not set until payment
        assert quiz_response.pdf_delivered_at is None

    @pytest.mark.asyncio
    async def test_submit_quiz_different_gender(self, client, valid_quiz_data, test_session: AsyncSession):
        """Test quiz submission with female gender (different BMR calculation)."""
        valid_quiz_data["quiz_data"]["step_1"] = "female"
        valid_quiz_data["email"] = "female@example.com"

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 200
        data = response.json()

        # Verify female calorie target is calculated
        assert data["calorie_target"] > 0

        # Female with same stats should have lower BMR than male
        # Age: 30, Weight: 75kg, Height: 175cm, Moderately Active, Weight Loss
        # Female BMR: 10*75 + 6.25*175 - 5*30 - 161 = 1532.75
        # TDEE: 1532.75 * 1.55 = 2375.76
        # With weight loss: 2375.76 - 400 = 1975.76 → 1976
        assert data["calorie_target"] == 1976

    @pytest.mark.asyncio
    async def test_submit_quiz_with_email_normalization(self, client, valid_quiz_data, test_session: AsyncSession):
        """Test email normalization for Gmail addresses (FR-P-010)."""
        # Gmail with dots and plus-tag
        valid_quiz_data["email"] = "Test.User+tag@gmail.com"

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 200
        data = response.json()

        # Verify database has normalized email
        quiz_id = data["quiz_id"]
        stmt = select(QuizResponse).where(QuizResponse.id == quiz_id)
        result = await test_session.execute(stmt)
        quiz_response = result.scalar_one_or_none()

        # Email is lowercased by Pydantic validator
        assert quiz_response.email == "test.user+tag@gmail.com"
        # Normalized email removes dots and plus-tags
        assert quiz_response.normalized_email == "testuser@gmail.com"


class TestCalorieCalculationIntegration:
    """Test calorie calculation integration (T041)."""

    @pytest.mark.asyncio
    async def test_weight_loss_goal_reduces_calories(self, client, valid_quiz_data):
        """Test weight loss goal applies -400 calorie adjustment."""
        valid_quiz_data["quiz_data"]["step_20"]["goal"] = "weight_loss"

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 200
        weight_loss_calories = response.json()["calorie_target"]

        # Change to maintenance
        valid_quiz_data["email"] = "maintenance@example.com"
        valid_quiz_data["quiz_data"]["step_20"]["goal"] = "maintenance"

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)
        maintenance_calories = response.json()["calorie_target"]

        # Weight loss should be 400 calories less than maintenance
        assert weight_loss_calories == maintenance_calories - 400

    @pytest.mark.asyncio
    async def test_muscle_gain_goal_increases_calories(self, client, valid_quiz_data):
        """Test muscle gain goal applies +250 calorie adjustment."""
        valid_quiz_data["quiz_data"]["step_20"]["goal"] = "maintenance"

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)
        maintenance_calories = response.json()["calorie_target"]

        # Change to muscle gain
        valid_quiz_data["email"] = "muscle@example.com"
        valid_quiz_data["quiz_data"]["step_20"]["goal"] = "muscle_gain"

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)
        muscle_gain_calories = response.json()["calorie_target"]

        # Muscle gain should be 250 calories more than maintenance
        assert muscle_gain_calories == maintenance_calories + 250

    @pytest.mark.asyncio
    async def test_activity_level_affects_calories(self, client, valid_quiz_data):
        """Test activity level multiplier affects calorie calculation."""
        # Test sedentary
        valid_quiz_data["quiz_data"]["step_2"] = "sedentary"
        valid_quiz_data["email"] = "sedentary@example.com"

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)
        sedentary_calories = response.json()["calorie_target"]

        # Test super active
        valid_quiz_data["quiz_data"]["step_2"] = "super_active"
        valid_quiz_data["email"] = "superactive@example.com"

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)
        super_active_calories = response.json()["calorie_target"]

        # Super active should have significantly more calories
        # Sedentary: 1.2, Super Active: 1.9
        assert super_active_calories > sedentary_calories
        assert super_active_calories - sedentary_calories > 500  # Significant difference

    @pytest.mark.asyncio
    async def test_calorie_floor_enforcement_female(self, client, valid_quiz_data):
        """Test female calorie floor (1200) is enforced."""
        # Very small, sedentary female aiming for aggressive weight loss
        valid_quiz_data["email"] = "petite@example.com"
        valid_quiz_data["quiz_data"]["step_1"] = "female"
        valid_quiz_data["quiz_data"]["step_2"] = "sedentary"
        valid_quiz_data["quiz_data"]["step_20"] = {
            "age": 50,
            "weight_kg": 45.0,
            "height_cm": 150.0,
            "goal": "weight_loss"
        }

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 200
        calorie_target = response.json()["calorie_target"]

        # Should hit female floor of 1200
        assert calorie_target == 1200

    @pytest.mark.asyncio
    async def test_calorie_floor_enforcement_male(self, client, valid_quiz_data):
        """Test male calorie floor (1500) is enforced."""
        # Very small, sedentary male aiming for aggressive weight loss
        valid_quiz_data["email"] = "small@example.com"
        valid_quiz_data["quiz_data"]["step_1"] = "male"
        valid_quiz_data["quiz_data"]["step_2"] = "sedentary"
        valid_quiz_data["quiz_data"]["step_20"] = {
            "age": 60,
            "weight_kg": 55.0,
            "height_cm": 160.0,
            "goal": "weight_loss"
        }

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 200
        calorie_target = response.json()["calorie_target"]

        # Should hit male floor of 1500
        assert calorie_target == 1500


class TestFoodItemValidation:
    """Test food item count validation (T042, FR-Q-017)."""

    @pytest.mark.asyncio
    async def test_minimum_10_items_enforced(self, client, valid_quiz_data):
        """Test that minimum 10 food items are required."""
        # Set only 9 items total
        valid_quiz_data["quiz_data"]["step_3"] = ["chicken"]  # 1
        valid_quiz_data["quiz_data"]["step_4"] = ["salmon"]  # 2
        valid_quiz_data["quiz_data"]["step_5"] = ["broccoli"]  # 3
        valid_quiz_data["quiz_data"]["step_6"] = ["cauliflower"]  # 4
        valid_quiz_data["quiz_data"]["step_7"] = ["kale"]  # 5
        valid_quiz_data["quiz_data"]["step_8"] = ["zucchini"]  # 6
        valid_quiz_data["quiz_data"]["step_9"] = ["beef"]  # 7
        valid_quiz_data["quiz_data"]["step_10"] = []  # 0
        valid_quiz_data["quiz_data"]["step_11"] = ["blueberries"]  # 8
        valid_quiz_data["quiz_data"]["step_12"] = ["almonds"]  # 9
        valid_quiz_data["quiz_data"]["step_13"] = []  # 0
        valid_quiz_data["quiz_data"]["step_14"] = []  # 0
        valid_quiz_data["quiz_data"]["step_15"] = []  # 0
        valid_quiz_data["quiz_data"]["step_16"] = []  # 0
        # Total: 9 items

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 400
        # Custom error handler format
        error_data = response.json()["error"]
        assert "at least 10 food items" in error_data["message"]
        assert "Currently selected: 9" in error_data["message"]

    @pytest.mark.asyncio
    async def test_exactly_10_items_allowed(self, client, valid_quiz_data):
        """Test that exactly 10 items passes validation."""
        # Set exactly 10 items
        valid_quiz_data["quiz_data"]["step_3"] = ["chicken", "turkey"]  # 2
        valid_quiz_data["quiz_data"]["step_4"] = ["salmon", "tuna"]  # 4
        valid_quiz_data["quiz_data"]["step_5"] = ["broccoli", "spinach"]  # 6
        valid_quiz_data["quiz_data"]["step_6"] = ["cauliflower"]  # 7
        valid_quiz_data["quiz_data"]["step_7"] = ["kale"]  # 8
        valid_quiz_data["quiz_data"]["step_8"] = ["zucchini"]  # 9
        valid_quiz_data["quiz_data"]["step_9"] = ["beef"]  # 10
        valid_quiz_data["quiz_data"]["step_10"] = []
        valid_quiz_data["quiz_data"]["step_11"] = []
        valid_quiz_data["quiz_data"]["step_12"] = []
        valid_quiz_data["quiz_data"]["step_13"] = []
        valid_quiz_data["quiz_data"]["step_14"] = []
        valid_quiz_data["quiz_data"]["step_15"] = []
        valid_quiz_data["quiz_data"]["step_16"] = []
        # Total: 10 items

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_zero_items_rejected(self, client, valid_quiz_data):
        """Test that 0 food items are rejected."""
        # Clear all food selections
        for step in range(3, 17):
            valid_quiz_data["quiz_data"][f"step_{step}"] = []

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 400
        # Custom error handler format
        error_data = response.json()["error"]
        assert "at least 10 food items" in error_data["message"]
        assert "Currently selected: 0" in error_data["message"]


class TestValidationErrors:
    """Test request validation and error handling."""

    @pytest.mark.asyncio
    async def test_missing_email_rejected(self, client, valid_quiz_data):
        """Test that missing email is rejected."""
        del valid_quiz_data["email"]

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_invalid_email_format_rejected(self, client, valid_quiz_data):
        """Test that invalid email format is rejected."""
        valid_quiz_data["email"] = "not-an-email"

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 422
        # Custom error handler format
        error_data = response.json()["error"]
        assert error_data["code"] == "validation_error"
        assert "fields" in error_data["details"]
        assert isinstance(error_data["details"]["fields"], list)

    @pytest.mark.asyncio
    async def test_invalid_gender_rejected(self, client, valid_quiz_data):
        """Test that invalid gender value is rejected."""
        valid_quiz_data["quiz_data"]["step_1"] = "other"

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_activity_level_rejected(self, client, valid_quiz_data):
        """Test that invalid activity level is rejected."""
        valid_quiz_data["quiz_data"]["step_2"] = "invalid_level"

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_goal_rejected(self, client, valid_quiz_data):
        """Test that invalid goal is rejected."""
        valid_quiz_data["quiz_data"]["step_20"]["goal"] = "invalid_goal"

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_age_too_young_rejected(self, client, valid_quiz_data):
        """Test that age < 18 is rejected."""
        valid_quiz_data["quiz_data"]["step_20"]["age"] = 17

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_age_too_old_rejected(self, client, valid_quiz_data):
        """Test that age > 100 is rejected."""
        valid_quiz_data["quiz_data"]["step_20"]["age"] = 101

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_dietary_restrictions_too_long_rejected(self, client, valid_quiz_data):
        """Test that dietary restrictions > 500 chars are rejected."""
        valid_quiz_data["quiz_data"]["step_17"] = "a" * 501

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_biometrics_rejected(self, client, valid_quiz_data):
        """Test that missing biometrics are rejected."""
        del valid_quiz_data["quiz_data"]["step_20"]

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 422


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_maximum_food_items(self, client, valid_quiz_data):
        """Test submission with maximum food selections."""
        # Fill all food steps with multiple items
        for step in range(3, 17):
            valid_quiz_data["quiz_data"][f"step_{step}"] = [
                f"item_{step}_{i}" for i in range(10)
            ]

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        # Should succeed - no upper limit on food items
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_boundary_age_18(self, client, valid_quiz_data):
        """Test boundary condition: age exactly 18."""
        valid_quiz_data["quiz_data"]["step_20"]["age"] = 18

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_boundary_age_100(self, client, valid_quiz_data):
        """Test boundary condition: age exactly 100."""
        valid_quiz_data["quiz_data"]["step_20"]["age"] = 100

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dietary_restrictions_exactly_500_chars(self, client, valid_quiz_data):
        """Test boundary condition: dietary restrictions exactly 500 characters."""
        valid_quiz_data["quiz_data"]["step_17"] = "a" * 500

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_dietary_restrictions(self, client, valid_quiz_data):
        """Test that empty dietary restrictions are allowed."""
        valid_quiz_data["quiz_data"]["step_17"] = ""

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_email_with_special_characters(self, client, valid_quiz_data):
        """Test email with valid special characters."""
        valid_quiz_data["email"] = "user+test.name@sub.example.co.uk"

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_whitespace_in_email_trimmed(self, client, valid_quiz_data):
        """Test that whitespace in email is trimmed."""
        valid_quiz_data["email"] = "  test@example.com  "

        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)

        assert response.status_code == 200


class TestDatabasePersistence:
    """Test database persistence and data integrity."""

    @pytest.mark.asyncio
    async def test_quiz_data_jsonb_storage(self, client, valid_quiz_data, test_session: AsyncSession):
        """Test that quiz_data is stored as JSONB and queryable."""
        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)
        quiz_id = response.json()["quiz_id"]

        # Query database
        stmt = select(QuizResponse).where(QuizResponse.id == quiz_id)
        result = await test_session.execute(stmt)
        quiz_response = result.scalar_one()

        # Verify JSONB structure is preserved
        assert quiz_response.quiz_data["step_1"] == "male"
        assert quiz_response.quiz_data["step_2"] == "moderately_active"
        assert isinstance(quiz_response.quiz_data["step_3"], list)
        assert quiz_response.quiz_data["step_20"]["age"] == 30
        assert quiz_response.quiz_data["step_17"] == "No shellfish please"

    @pytest.mark.asyncio
    async def test_multiple_submissions_same_email(self, client, valid_quiz_data, test_session: AsyncSession):
        """Test that multiple quiz submissions with same email create separate records."""
        # Use a unique email to avoid conflicts with other tests
        test_email = f"multi-test-{uuid.uuid4().hex[:8]}@example.com"
        valid_quiz_data["email"] = test_email

        # First submission
        response1 = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)
        quiz_id1 = response1.json()["quiz_id"]

        # Second submission with same email
        response2 = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)
        quiz_id2 = response2.json()["quiz_id"]

        # Should create two separate records
        assert quiz_id1 != quiz_id2

        # Verify both exist in database
        stmt = select(QuizResponse).where(
            QuizResponse.email == test_email
        )
        result = await test_session.execute(stmt)
        results = result.scalars().all()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_timestamps_set_automatically(self, client, valid_quiz_data, test_session: AsyncSession):
        """Test that created_at timestamp is set automatically."""
        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)
        quiz_id = response.json()["quiz_id"]

        # Query database
        stmt = select(QuizResponse).where(QuizResponse.id == quiz_id)
        result = await test_session.execute(stmt)
        quiz_response = result.scalar_one()

        # Verify timestamp
        assert quiz_response.created_at is not None
        assert quiz_response.pdf_delivered_at is None  # Not delivered yet

    @pytest.mark.asyncio
    async def test_null_user_id_for_unauthenticated_flow(self, client, valid_quiz_data, test_session: AsyncSession):
        """Test that user_id is NULL for unauthenticated quiz submission (FR-Q-020)."""
        response = await client.post("/api/v1/quiz/submit", json=valid_quiz_data)
        quiz_id = response.json()["quiz_id"]

        # Query database
        stmt = select(QuizResponse).where(QuizResponse.id == quiz_id)
        result = await test_session.execute(stmt)
        quiz_response = result.scalar_one()

        # Should be NULL for unauthenticated flow
        assert quiz_response.user_id is None


class TestRealWorldScenarios:
    """Test realistic end-to-end scenarios."""

    @pytest.mark.asyncio
    async def test_typical_weight_loss_female_scenario(self, client):
        """Test typical female weight loss scenario."""
        quiz_data = {
            "email": "sarah@example.com",
            "quiz_data": {
                "step_1": "female",
                "step_2": "lightly_active",
                "step_3": ["chicken", "turkey"],
                "step_4": ["salmon"],
                "step_5": ["broccoli", "spinach", "bell_peppers"],
                "step_6": ["cauliflower"],
                "step_7": ["kale", "lettuce"],
                "step_8": ["cucumber"],
                "step_9": [],
                "step_10": [],
                "step_11": ["strawberries"],
                "step_12": ["walnuts"],
                "step_13": ["basil", "pepper"],
                "step_14": ["avocado_oil"],
                "step_15": ["coffee", "green_tea"],
                "step_16": ["greek_yogurt"],
                "step_17": "Lactose intolerant, prefer dairy alternatives",
                "step_18": "3",
                "step_19": ["meal_prep"],
                "step_20": {
                    "age": 35,
                    "weight_kg": 70.0,
                    "height_cm": 165.0,
                    "goal": "weight_loss"
                }
            }
        }

        response = await client.post("/api/v1/quiz/submit", json=quiz_data)

        assert response.status_code == 200
        data = response.json()

        # Verify reasonable calorie target for this profile
        # Female, 35yo, 70kg, 165cm, lightly active, weight loss
        # BMR: 10*70 + 6.25*165 - 5*35 - 161 = 1395.25
        # TDEE: 1395.25 * 1.375 = 1918.47
        # Weight loss: 1918.47 - 400 = 1518.47 → 1518
        assert data["calorie_target"] == 1518

    @pytest.mark.asyncio
    async def test_typical_muscle_gain_male_scenario(self, client):
        """Test typical male muscle gain scenario."""
        quiz_data = {
            "email": "mike@example.com",
            "quiz_data": {
                "step_1": "male",
                "step_2": "very_active",
                "step_3": ["chicken", "turkey", "duck"],
                "step_4": ["salmon", "mackerel"],
                "step_5": ["broccoli", "asparagus"],
                "step_6": ["brussels_sprouts"],
                "step_7": ["spinach"],
                "step_8": ["mushrooms"],
                "step_9": ["beef", "pork", "lamb"],
                "step_10": ["liver"],
                "step_11": [],
                "step_12": ["almonds", "pecans"],
                "step_13": ["garlic", "rosemary"],
                "step_14": ["coconut_oil", "butter"],
                "step_15": ["protein_shake"],
                "step_16": ["whole_milk", "cheese"],
                "step_17": "",
                "step_18": "4",
                "step_19": ["gym_workout", "meal_prep"],
                "step_20": {
                    "age": 28,
                    "weight_kg": 80.0,
                    "height_cm": 180.0,
                    "goal": "muscle_gain"
                }
            }
        }

        response = await client.post("/api/v1/quiz/submit", json=quiz_data)

        assert response.status_code == 200
        data = response.json()

        # Verify reasonable calorie target for this profile
        # Male, 28yo, 80kg, 180cm, very active, muscle gain
        # BMR: 10*80 + 6.25*180 - 5*28 + 5 = 1790
        # TDEE: 1790 * 1.725 = 3087.75
        # Muscle gain: 3087.75 + 250 = 3337.75 → 3338
        assert data["calorie_target"] == 3338

    @pytest.mark.asyncio
    async def test_maintenance_scenario_with_many_restrictions(self, client):
        """Test maintenance goal with extensive dietary restrictions."""
        quiz_data = {
            "email": "alex@example.com",
            "quiz_data": {
                "step_1": "female",
                "step_2": "moderately_active",
                "step_3": ["turkey"],
                "step_4": ["salmon", "cod", "halibut"],
                "step_5": ["broccoli", "zucchini"],
                "step_6": ["cauliflower"],
                "step_7": ["spinach", "arugula"],
                "step_8": [],
                "step_9": [],
                "step_10": [],
                "step_11": ["raspberries"],
                "step_12": ["chia_seeds"],
                "step_13": ["turmeric"],
                "step_14": ["olive_oil"],
                "step_15": ["herbal_tea"],
                "step_16": [],
                "step_17": "No dairy, no red meat, no nightshades (tomatoes, peppers, eggplant). Prefer fish and poultry only.",
                "step_18": "3",
                "step_19": ["vegetarian_leaning"],
                "step_20": {
                    "age": 42,
                    "weight_kg": 65.0,
                    "height_cm": 170.0,
                    "goal": "maintenance"
                }
            }
        }

        response = await client.post("/api/v1/quiz/submit", json=quiz_data)

        assert response.status_code == 200
        data = response.json()

        # Should process successfully despite restrictions
        assert data["success"] is True
        assert data["calorie_target"] > 0
