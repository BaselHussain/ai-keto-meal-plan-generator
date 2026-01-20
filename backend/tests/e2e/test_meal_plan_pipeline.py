"""
End-to-end tests for the full meal plan delivery pipeline.

Tests: T089H - E2E pipeline tests (3 test cases)

Pipeline Flow (with mocked webhook trigger):
1. Webhook received (mocked) → triggers orchestration
2. AI meal plan generation → creates 30-day keto plan
3. PDF creation → generates ReportLab PDF
4. Blob upload → uploads to Vercel Blob
5. Email sent → delivers PDF via Resend

Test Cases:
1. test_full_pipeline_weight_loss_profile - Weight loss goal (calorie deficit)
2. test_full_pipeline_muscle_gain_profile - Muscle gain goal (calorie surplus)
3. test_full_pipeline_maintenance_profile - Maintenance goal (balanced calories)

Performance Requirement:
- Full pipeline must complete in <90 seconds (p95)

Dependencies:
- All services mocked to avoid external API calls
- Database operations mocked for isolation
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import List

from src.schemas.meal_plan import (
    MealPlanStructure,
    DayMealPlan,
    Meal,
    WeeklyShoppingList,
    Ingredient,
    PreferencesSummary,
)


# ============================================================
# Test Fixtures: Quiz Profiles
# ============================================================

def create_weight_loss_profile() -> dict:
    """Create quiz data for weight loss profile."""
    return {
        "email": "weightloss@example.com",
        "gender": "female",
        "age": 35,
        "height_feet": 5,
        "height_inches": 4,
        "weight_lbs": 180,
        "goal": "lose_weight",
        "activity_level": "moderate",
        "excluded_foods": ["pork", "shellfish"],
        "preferred_proteins": ["chicken", "fish", "eggs"],
        "dietary_restrictions": "No dairy",
        "calorie_target": 1400,  # Deficit for weight loss
        "preferences_summary": {
            "excluded_foods": ["pork", "shellfish"],
            "preferred_proteins": ["chicken", "fish", "eggs"],
            "dietary_restrictions": "No dairy",
        },
    }


def create_muscle_gain_profile() -> dict:
    """Create quiz data for muscle gain profile."""
    return {
        "email": "musclegain@example.com",
        "gender": "male",
        "age": 28,
        "height_feet": 6,
        "height_inches": 0,
        "weight_lbs": 175,
        "goal": "build_muscle",
        "activity_level": "very_active",
        "excluded_foods": ["nuts"],
        "preferred_proteins": ["beef", "chicken", "salmon"],
        "dietary_restrictions": "",
        "calorie_target": 2800,  # Surplus for muscle gain
        "preferences_summary": {
            "excluded_foods": ["nuts"],
            "preferred_proteins": ["beef", "chicken", "salmon"],
            "dietary_restrictions": "",
        },
    }


def create_maintenance_profile() -> dict:
    """Create quiz data for maintenance profile."""
    return {
        "email": "maintenance@example.com",
        "gender": "male",
        "age": 42,
        "height_feet": 5,
        "height_inches": 10,
        "weight_lbs": 165,
        "goal": "maintain",
        "activity_level": "light",
        "excluded_foods": [],
        "preferred_proteins": ["chicken", "beef", "fish", "pork"],
        "dietary_restrictions": "",
        "calorie_target": 2000,  # Maintenance calories
        "preferences_summary": {
            "excluded_foods": [],
            "preferred_proteins": ["chicken", "beef", "fish", "pork"],
            "dietary_restrictions": "",
        },
    }


# ============================================================
# Mock Helpers
# ============================================================

def create_mock_meal(name: str, carbs: int = 8) -> Meal:
    """Create a valid mock meal."""
    return Meal(
        name=name,
        recipe=f"Delicious {name.title()} Recipe",
        ingredients=["ingredient1", "ingredient2", "ingredient3"],
        prep_time=15,
        calories=600,
        protein=30,
        carbs=carbs,
        fat=45,
    )


def create_mock_day(day_num: int) -> DayMealPlan:
    """Create a valid mock day meal plan."""
    return DayMealPlan(
        day=day_num,
        meals=[
            create_mock_meal("breakfast", 7),
            create_mock_meal("lunch", 8),
            create_mock_meal("dinner", 9),
        ],
        total_calories=1800,
        total_protein=90,
        total_carbs=24,  # Under 30g for keto
        total_fat=135,
    )


def create_mock_meal_plan() -> MealPlanStructure:
    """Create a complete mock 30-day meal plan."""
    return MealPlanStructure(
        days=[create_mock_day(i) for i in range(1, 31)],
        shopping_lists=[
            WeeklyShoppingList(
                week=1,
                proteins=[
                    Ingredient(name="eggs", quantity="2 dozen"),
                    Ingredient(name="chicken", quantity="3 lbs"),
                ],
                vegetables=[
                    Ingredient(name="spinach", quantity="2 bunches"),
                    Ingredient(name="broccoli", quantity="2 heads"),
                ],
            ),
            WeeklyShoppingList(
                week=2,
                proteins=[
                    Ingredient(name="beef", quantity="2 lbs"),
                    Ingredient(name="salmon", quantity="1 lb"),
                ],
                vegetables=[
                    Ingredient(name="asparagus", quantity="1 bunch"),
                    Ingredient(name="zucchini", quantity="3"),
                ],
            ),
            WeeklyShoppingList(
                week=3,
                proteins=[
                    Ingredient(name="pork chops", quantity="4"),
                    Ingredient(name="shrimp", quantity="1 lb"),
                ],
                vegetables=[
                    Ingredient(name="kale", quantity="1 bunch"),
                    Ingredient(name="cauliflower", quantity="1 head"),
                ],
            ),
            WeeklyShoppingList(
                week=4,
                proteins=[
                    Ingredient(name="lamb", quantity="1 lb"),
                    Ingredient(name="tuna", quantity="3 cans"),
                ],
                vegetables=[
                    Ingredient(name="brussels sprouts", quantity="1 lb"),
                    Ingredient(name="bell peppers", quantity="4"),
                ],
            ),
        ],
    )


class MockDBSession:
    """Mock async database session for testing."""

    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.meal_plans = {}

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def flush(self):
        pass

    async def execute(self, query):
        """Mock query execution."""
        class Result:
            def scalar_one_or_none(self):
                return None
        return Result()

    def add(self, obj):
        """Mock add object to session."""
        if hasattr(obj, 'payment_id'):
            self.meal_plans[obj.payment_id] = obj


class MockMealPlan:
    """Mock MealPlan model for testing."""

    def __init__(
        self,
        id: str,
        payment_id: str,
        email: str,
        normalized_email: str,
        calorie_target: int,
        preferences_summary: dict,
    ):
        self.id = id
        self.payment_id = payment_id
        self.email = email
        self.normalized_email = normalized_email
        self.calorie_target = calorie_target
        self.preferences_summary = preferences_summary
        self.pdf_blob_path = ""
        self.ai_model = "pending"
        self.status = "processing"
        self.email_sent_at = None
        self.refund_count = 0
        self.created_at = datetime.utcnow()


# ============================================================
# E2E Pipeline Tests
# ============================================================

class TestFullPipelineWeightLoss:
    """Test case 1: Full pipeline with weight loss profile."""

    @pytest.mark.asyncio
    async def test_full_pipeline_weight_loss_profile(self):
        """
        E2E test: Full pipeline with weight loss quiz profile.

        Verifies:
        - Pipeline completes successfully
        - All 5 steps executed (idempotency, record, AI, PDF, blob, email)
        - Total duration <90 seconds
        - Calorie target matches weight loss goal (deficit)
        """
        profile = create_weight_loss_profile()
        payment_id = "pay_weightloss_123"

        # Track step execution
        steps_executed = []

        # Mock AI generation
        async def mock_generate_meal_plan(calorie_target, preferences):
            steps_executed.append("ai_generation")
            await asyncio.sleep(0.1)  # Simulate some work
            return {
                "success": True,
                "meal_plan": create_mock_meal_plan(),
                "model_used": "gpt-4",
                "generation_time_ms": 5000,
            }

        # Mock PDF generation
        async def mock_generate_pdf(meal_plan, calorie_target, user_email):
            steps_executed.append("pdf_generation")
            await asyncio.sleep(0.05)
            # Return valid PDF bytes
            return b'%PDF-1.4\nMock PDF Content\n%%EOF'

        # Mock blob upload
        async def mock_upload_blob(pdf_bytes, filename):
            steps_executed.append("blob_upload")
            await asyncio.sleep(0.05)
            return f"https://blob.vercel-storage.com/{filename}"

        # Mock email delivery
        async def mock_send_email(**kwargs):
            steps_executed.append("email_delivery")
            await asyncio.sleep(0.05)
            return {
                "success": True,
                "message_id": "msg_weightloss_123",
                "sent_at": datetime.utcnow(),
            }

        # Mock database operations
        mock_db = MockDBSession()

        with patch('src.services.delivery_orchestrator.generate_meal_plan', mock_generate_meal_plan), \
             patch('src.services.delivery_orchestrator.generate_pdf', mock_generate_pdf), \
             patch('src.services.delivery_orchestrator.upload_pdf_to_vercel_blob', mock_upload_blob), \
             patch('src.services.delivery_orchestrator.send_delivery_email', mock_send_email), \
             patch('src.services.delivery_orchestrator._check_existing_meal_plan', AsyncMock(return_value=None)), \
             patch('src.services.delivery_orchestrator._create_meal_plan_record') as mock_create_record, \
             patch('src.services.delivery_orchestrator._update_meal_plan_status', AsyncMock()):

            # Setup mock record creation
            mock_meal_plan = MockMealPlan(
                id="mp_weightloss_123",
                payment_id=payment_id,
                email=profile["email"],
                normalized_email=profile["email"].lower(),
                calorie_target=profile["calorie_target"],
                preferences_summary=profile["preferences_summary"],
            )
            mock_create_record.return_value = mock_meal_plan

            from src.services.delivery_orchestrator import orchestrate_meal_plan_delivery

            start_time = time.time()

            result = await orchestrate_meal_plan_delivery(
                payment_id=payment_id,
                email=profile["email"],
                normalized_email=profile["email"].lower(),
                quiz_data=profile,
                calorie_target=profile["calorie_target"],
                preferences_summary=profile["preferences_summary"],
                db=mock_db,
            )

            elapsed_time = time.time() - start_time

            # Assertions
            assert result["success"] == True, f"Pipeline failed: {result.get('error')}"
            assert result["meal_plan_id"] == "mp_weightloss_123"
            assert result["requires_manual_resolution"] == False

            # Verify all steps executed
            assert "ai_generation" in steps_executed
            assert "pdf_generation" in steps_executed
            assert "blob_upload" in steps_executed
            assert "email_delivery" in steps_executed

            # Verify performance requirement (<90 seconds)
            assert elapsed_time < 90, f"Pipeline took {elapsed_time:.2f}s, exceeds 90s limit"

            # Verify calorie target for weight loss
            assert profile["calorie_target"] == 1400  # Deficit


class TestFullPipelineMuscleGain:
    """Test case 2: Full pipeline with muscle gain profile."""

    @pytest.mark.asyncio
    async def test_full_pipeline_muscle_gain_profile(self):
        """
        E2E test: Full pipeline with muscle gain quiz profile.

        Verifies:
        - Pipeline completes successfully with high calorie target
        - All steps executed in order
        - Total duration <90 seconds
        - Calorie target matches muscle gain goal (surplus)
        """
        profile = create_muscle_gain_profile()
        payment_id = "pay_musclegain_456"

        steps_executed = []

        async def mock_generate_meal_plan(calorie_target, preferences):
            steps_executed.append("ai_generation")
            # Verify high calorie target for muscle gain
            assert calorie_target == 2800
            return {
                "success": True,
                "meal_plan": create_mock_meal_plan(),
                "model_used": "gpt-4",
                "generation_time_ms": 6000,
            }

        async def mock_generate_pdf(meal_plan, calorie_target, user_email):
            steps_executed.append("pdf_generation")
            assert calorie_target == 2800
            return b'%PDF-1.4\nMock PDF Content for Muscle Gain\n%%EOF'

        async def mock_upload_blob(pdf_bytes, filename):
            steps_executed.append("blob_upload")
            return f"https://blob.vercel-storage.com/{filename}"

        async def mock_send_email(**kwargs):
            steps_executed.append("email_delivery")
            assert kwargs["calorie_target"] == 2800
            return {
                "success": True,
                "message_id": "msg_musclegain_456",
                "sent_at": datetime.utcnow(),
            }

        mock_db = MockDBSession()

        with patch('src.services.delivery_orchestrator.generate_meal_plan', mock_generate_meal_plan), \
             patch('src.services.delivery_orchestrator.generate_pdf', mock_generate_pdf), \
             patch('src.services.delivery_orchestrator.upload_pdf_to_vercel_blob', mock_upload_blob), \
             patch('src.services.delivery_orchestrator.send_delivery_email', mock_send_email), \
             patch('src.services.delivery_orchestrator._check_existing_meal_plan', AsyncMock(return_value=None)), \
             patch('src.services.delivery_orchestrator._create_meal_plan_record') as mock_create_record, \
             patch('src.services.delivery_orchestrator._update_meal_plan_status', AsyncMock()):

            mock_meal_plan = MockMealPlan(
                id="mp_musclegain_456",
                payment_id=payment_id,
                email=profile["email"],
                normalized_email=profile["email"].lower(),
                calorie_target=profile["calorie_target"],
                preferences_summary=profile["preferences_summary"],
            )
            mock_create_record.return_value = mock_meal_plan

            from src.services.delivery_orchestrator import orchestrate_meal_plan_delivery

            start_time = time.time()

            result = await orchestrate_meal_plan_delivery(
                payment_id=payment_id,
                email=profile["email"],
                normalized_email=profile["email"].lower(),
                quiz_data=profile,
                calorie_target=profile["calorie_target"],
                preferences_summary=profile["preferences_summary"],
                db=mock_db,
            )

            elapsed_time = time.time() - start_time

            # Assertions
            assert result["success"] == True, f"Pipeline failed: {result.get('error')}"
            assert result["meal_plan_id"] == "mp_musclegain_456"

            # Verify all steps executed
            assert len(steps_executed) == 4
            assert steps_executed == ["ai_generation", "pdf_generation", "blob_upload", "email_delivery"]

            # Verify performance
            assert elapsed_time < 90

            # Verify calorie target for muscle gain
            assert profile["calorie_target"] == 2800  # Surplus


class TestFullPipelineMaintenance:
    """Test case 3: Full pipeline with maintenance profile."""

    @pytest.mark.asyncio
    async def test_full_pipeline_maintenance_profile(self):
        """
        E2E test: Full pipeline with maintenance quiz profile.

        Verifies:
        - Pipeline completes successfully with balanced calories
        - All steps executed correctly
        - Total duration <90 seconds
        - Calorie target matches maintenance goal
        """
        profile = create_maintenance_profile()
        payment_id = "pay_maintenance_789"

        steps_executed = []
        step_durations = {}

        async def mock_generate_meal_plan(calorie_target, preferences):
            start = time.time()
            steps_executed.append("ai_generation")
            await asyncio.sleep(0.1)
            step_durations["ai_generation"] = time.time() - start
            return {
                "success": True,
                "meal_plan": create_mock_meal_plan(),
                "model_used": "gpt-4",
                "generation_time_ms": 4500,
            }

        async def mock_generate_pdf(meal_plan, calorie_target, user_email):
            start = time.time()
            steps_executed.append("pdf_generation")
            await asyncio.sleep(0.05)
            step_durations["pdf_generation"] = time.time() - start
            return b'%PDF-1.4\nMock PDF Content for Maintenance\n%%EOF'

        async def mock_upload_blob(pdf_bytes, filename):
            start = time.time()
            steps_executed.append("blob_upload")
            await asyncio.sleep(0.05)
            step_durations["blob_upload"] = time.time() - start
            return f"https://blob.vercel-storage.com/{filename}"

        async def mock_send_email(**kwargs):
            start = time.time()
            steps_executed.append("email_delivery")
            await asyncio.sleep(0.05)
            step_durations["email_delivery"] = time.time() - start
            return {
                "success": True,
                "message_id": "msg_maintenance_789",
                "sent_at": datetime.utcnow(),
            }

        mock_db = MockDBSession()

        with patch('src.services.delivery_orchestrator.generate_meal_plan', mock_generate_meal_plan), \
             patch('src.services.delivery_orchestrator.generate_pdf', mock_generate_pdf), \
             patch('src.services.delivery_orchestrator.upload_pdf_to_vercel_blob', mock_upload_blob), \
             patch('src.services.delivery_orchestrator.send_delivery_email', mock_send_email), \
             patch('src.services.delivery_orchestrator._check_existing_meal_plan', AsyncMock(return_value=None)), \
             patch('src.services.delivery_orchestrator._create_meal_plan_record') as mock_create_record, \
             patch('src.services.delivery_orchestrator._update_meal_plan_status', AsyncMock()):

            mock_meal_plan = MockMealPlan(
                id="mp_maintenance_789",
                payment_id=payment_id,
                email=profile["email"],
                normalized_email=profile["email"].lower(),
                calorie_target=profile["calorie_target"],
                preferences_summary=profile["preferences_summary"],
            )
            mock_create_record.return_value = mock_meal_plan

            from src.services.delivery_orchestrator import orchestrate_meal_plan_delivery

            start_time = time.time()

            result = await orchestrate_meal_plan_delivery(
                payment_id=payment_id,
                email=profile["email"],
                normalized_email=profile["email"].lower(),
                quiz_data=profile,
                calorie_target=profile["calorie_target"],
                preferences_summary=profile["preferences_summary"],
                db=mock_db,
            )

            total_elapsed = time.time() - start_time

            # Assertions
            assert result["success"] == True, f"Pipeline failed: {result.get('error')}"
            assert result["meal_plan_id"] == "mp_maintenance_789"

            # Verify all steps executed in correct order
            assert steps_executed == ["ai_generation", "pdf_generation", "blob_upload", "email_delivery"]

            # Verify performance (<90 seconds)
            assert total_elapsed < 90, f"Pipeline took {total_elapsed:.2f}s"

            # Verify calorie target for maintenance
            assert profile["calorie_target"] == 2000  # Maintenance

            # Verify result contains duration
            assert "total_duration_ms" in result
            assert result["total_duration_ms"] >= 0


class TestPipelinePerformance:
    """Additional tests for pipeline performance requirements."""

    @pytest.mark.asyncio
    async def test_pipeline_completes_under_90_seconds(self):
        """Verify pipeline can complete within 90-second budget even with delays."""
        profile = create_weight_loss_profile()
        payment_id = "pay_perf_test"

        # Simulate realistic delays
        async def mock_generate_meal_plan(calorie_target, preferences):
            await asyncio.sleep(0.5)  # Simulate AI generation time
            return {
                "success": True,
                "meal_plan": create_mock_meal_plan(),
                "model_used": "gpt-4",
                "generation_time_ms": 500,
            }

        async def mock_generate_pdf(meal_plan, calorie_target, user_email):
            await asyncio.sleep(0.2)  # Simulate PDF generation
            return b'%PDF-1.4\nContent\n%%EOF'

        async def mock_upload_blob(pdf_bytes, filename):
            await asyncio.sleep(0.1)  # Simulate network upload
            return "https://blob.vercel-storage.com/test.pdf"

        async def mock_send_email(**kwargs):
            await asyncio.sleep(0.1)  # Simulate email API
            return {"success": True, "message_id": "msg_perf", "sent_at": datetime.utcnow()}

        mock_db = MockDBSession()

        with patch('src.services.delivery_orchestrator.generate_meal_plan', mock_generate_meal_plan), \
             patch('src.services.delivery_orchestrator.generate_pdf', mock_generate_pdf), \
             patch('src.services.delivery_orchestrator.upload_pdf_to_vercel_blob', mock_upload_blob), \
             patch('src.services.delivery_orchestrator.send_delivery_email', mock_send_email), \
             patch('src.services.delivery_orchestrator._check_existing_meal_plan', AsyncMock(return_value=None)), \
             patch('src.services.delivery_orchestrator._create_meal_plan_record') as mock_create, \
             patch('src.services.delivery_orchestrator._update_meal_plan_status', AsyncMock()):

            mock_meal_plan = MockMealPlan(
                id="mp_perf",
                payment_id=payment_id,
                email=profile["email"],
                normalized_email=profile["email"].lower(),
                calorie_target=profile["calorie_target"],
                preferences_summary=profile["preferences_summary"],
            )
            mock_create.return_value = mock_meal_plan

            from src.services.delivery_orchestrator import orchestrate_meal_plan_delivery

            start = time.time()

            result = await orchestrate_meal_plan_delivery(
                payment_id=payment_id,
                email=profile["email"],
                normalized_email=profile["email"].lower(),
                quiz_data=profile,
                calorie_target=profile["calorie_target"],
                preferences_summary=profile["preferences_summary"],
                db=mock_db,
            )

            elapsed = time.time() - start

            assert result["success"] == True
            assert elapsed < 90, f"Pipeline took {elapsed:.2f}s, exceeds 90s budget"
            # Should complete in about 1 second with our mock delays
            assert elapsed < 2, f"Pipeline took longer than expected: {elapsed:.2f}s"


class TestPipelineErrorRecovery:
    """Tests for pipeline error handling and recovery."""

    @pytest.mark.asyncio
    async def test_pipeline_handles_ai_generation_failure(self):
        """Verify pipeline handles AI generation failure gracefully."""
        profile = create_weight_loss_profile()
        payment_id = "pay_ai_fail"

        async def mock_generate_meal_plan_fail(calorie_target, preferences):
            return {
                "success": False,
                "validation_errors": ["AI generation failed"],
                "error_type": "ai_generation_failed",
            }

        mock_db = MockDBSession()

        with patch('src.services.delivery_orchestrator.generate_meal_plan', mock_generate_meal_plan_fail), \
             patch('src.services.delivery_orchestrator._check_existing_meal_plan', AsyncMock(return_value=None)), \
             patch('src.services.delivery_orchestrator._create_meal_plan_record') as mock_create, \
             patch('src.services.delivery_orchestrator._update_meal_plan_status', AsyncMock()), \
             patch('src.services.delivery_orchestrator._create_manual_resolution_entry', AsyncMock()):

            mock_meal_plan = MockMealPlan(
                id="mp_ai_fail",
                payment_id=payment_id,
                email=profile["email"],
                normalized_email=profile["email"].lower(),
                calorie_target=profile["calorie_target"],
                preferences_summary=profile["preferences_summary"],
            )
            mock_create.return_value = mock_meal_plan

            from src.services.delivery_orchestrator import orchestrate_meal_plan_delivery

            result = await orchestrate_meal_plan_delivery(
                payment_id=payment_id,
                email=profile["email"],
                normalized_email=profile["email"].lower(),
                quiz_data=profile,
                calorie_target=profile["calorie_target"],
                preferences_summary=profile["preferences_summary"],
                db=mock_db,
            )

            # Pipeline should fail but handle it gracefully
            assert result["success"] == False
            assert result["requires_manual_resolution"] == True
            assert "ai_generation" in result.get("error", "").lower() or result["error"] is not None


class TestPipelineIdempotency:
    """Tests for pipeline idempotency."""

    @pytest.mark.asyncio
    async def test_pipeline_skips_completed_meal_plan(self):
        """Verify pipeline skips if meal plan already completed."""
        profile = create_weight_loss_profile()
        payment_id = "pay_already_done"

        # Create a "completed" meal plan
        existing_meal_plan = MockMealPlan(
            id="mp_existing",
            payment_id=payment_id,
            email=profile["email"],
            normalized_email=profile["email"].lower(),
            calorie_target=profile["calorie_target"],
            preferences_summary=profile["preferences_summary"],
        )
        existing_meal_plan.status = "completed"

        mock_db = MockDBSession()

        with patch('src.services.delivery_orchestrator._check_existing_meal_plan',
                   AsyncMock(return_value=existing_meal_plan)):

            from src.services.delivery_orchestrator import orchestrate_meal_plan_delivery

            result = await orchestrate_meal_plan_delivery(
                payment_id=payment_id,
                email=profile["email"],
                normalized_email=profile["email"].lower(),
                quiz_data=profile,
                calorie_target=profile["calorie_target"],
                preferences_summary=profile["preferences_summary"],
                db=mock_db,
            )

            # Should succeed immediately without running any steps
            assert result["success"] == True
            assert result["meal_plan_id"] == "mp_existing"
            assert "already_completed" in result["steps_completed"]
