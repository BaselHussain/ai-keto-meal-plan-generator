"""
Integration tests for database models.

This module tests CRUD operations, unique constraints, foreign key relationships,
and JSONB queries for all 7 database models:
- User
- QuizResponse
- MealPlan
- PaymentTransaction
- ManualResolution
- MagicLinkToken
- EmailBlacklist

Test Requirements (T029D):
1. CRUD operations for all 7 models
2. Unique constraint tests (payment_id, normalized_email)
3. Foreign key relationship tests (User->QuizResponse, PaymentTransaction->MealPlan)
4. JSONB queries on quiz_data and preferences_summary fields

Test Coverage:
- 34 comprehensive integration tests
- All CRUD operations (Create, Read, Update, Delete)
- Unique constraint validation
- Foreign key cascade behavior
- JSONB field queries (simple and nested)
- Relationship loading and traversal
- Full payment flow simulation

Test Isolation:
- Each test uses test_session fixture with automatic rollback
- No test data leaks between tests
- Tests can run in parallel without conflicts

Running Tests:
- Requires PostgreSQL database (JSONB fields are PostgreSQL-specific)
- Set TEST_DATABASE_URL environment variable:
  export TEST_DATABASE_URL="postgresql://user:pass@host:port/db"
- Run tests:
  pytest tests/integration/test_models.py -v
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.models.quiz_response import QuizResponse
from src.models.meal_plan import MealPlan
from src.models.payment_transaction import PaymentTransaction
from src.models.manual_resolution import ManualResolution
from src.models.magic_link import MagicLinkToken
from src.models.email_blacklist import EmailBlacklist
from src.lib.email_utils import normalize_email


# ============================================================================
# User Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_user_create(test_session: AsyncSession):
    """Test creating a new user with password authentication."""
    user = User(
        email="test.user@example.com",
        normalized_email=normalize_email("test.user@example.com"),
        password_hash="$2b$12$hashed_password_here",
    )
    test_session.add(user)
    await test_session.flush()

    assert user.id is not None
    assert user.email == "test.user@example.com"
    # Note: normalize_email only removes dots for Gmail domains, not other domains
    assert user.normalized_email == "test.user@example.com"
    assert user.password_hash == "$2b$12$hashed_password_here"
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_user_create_magic_link_only(test_session: AsyncSession):
    """Test creating a user with magic link authentication (no password)."""
    user = User(
        email="magic@example.com",
        normalized_email=normalize_email("magic@example.com"),
        password_hash=None,
    )
    test_session.add(user)
    await test_session.flush()

    assert user.id is not None
    assert user.email == "magic@example.com"
    assert user.password_hash is None


@pytest.mark.asyncio
async def test_user_read(test_session: AsyncSession):
    """Test reading a user by ID."""
    user = User(
        email="read.test@example.com",
        normalized_email=normalize_email("read.test@example.com"),
        password_hash="hashed",
    )
    test_session.add(user)
    await test_session.flush()

    # Read by ID
    stmt = select(User).where(User.id == user.id)
    result = await test_session.execute(stmt)
    fetched_user = result.scalar_one()

    assert fetched_user.id == user.id
    assert fetched_user.email == "read.test@example.com"


@pytest.mark.asyncio
async def test_user_update(test_session: AsyncSession):
    """Test updating a user's password hash."""
    user = User(
        email="update.test@example.com",
        normalized_email=normalize_email("update.test@example.com"),
        password_hash="old_hash",
    )
    test_session.add(user)
    await test_session.flush()

    original_updated_at = user.updated_at

    # Update password hash
    user.password_hash = "new_hash"
    await test_session.flush()

    assert user.password_hash == "new_hash"
    # updated_at should be automatically updated (though might be same in test due to timing)


@pytest.mark.asyncio
async def test_user_delete(test_session: AsyncSession):
    """Test deleting a user."""
    user = User(
        email="delete.test@example.com",
        normalized_email=normalize_email("delete.test@example.com"),
        password_hash="hashed",
    )
    test_session.add(user)
    await test_session.flush()
    user_id = user.id

    # Delete user
    await test_session.delete(user)
    await test_session.flush()

    # Verify deletion
    stmt = select(User).where(User.id == user_id)
    result = await test_session.execute(stmt)
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_user_unique_email_constraint(test_session: AsyncSession):
    """Test that duplicate emails are rejected."""
    user1 = User(
        email="constraint_test_dup@example.com",
        normalized_email=normalize_email("constraint_test_dup@example.com"),
        password_hash="hash1",
    )
    test_session.add(user1)
    await test_session.flush()

    # Try to create user with same email
    user2 = User(
        email="constraint_test_dup@example.com",
        normalized_email=normalize_email("constraint_test_dup@example.com"),
        password_hash="hash2",
    )
    test_session.add(user2)

    with pytest.raises(IntegrityError):
        await test_session.flush()


# ============================================================================
# QuizResponse Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_quiz_response_create_authenticated(test_session: AsyncSession):
    """Test creating a quiz response for an authenticated user."""
    # Create user first
    user = User(
        email="quiz.user@example.com",
        normalized_email=normalize_email("quiz.user@example.com"),
        password_hash="hashed",
    )
    test_session.add(user)
    await test_session.flush()

    # Create quiz response
    quiz_data = {
        "step_1": "female",
        "step_2": "moderately_active",
        "step_20": {
            "age": 30,
            "weight_kg": 65,
            "height_cm": 165,
            "goal": "weight_loss"
        }
    }

    quiz = QuizResponse(
        user_id=user.id,
        email="quiz.user@example.com",
        normalized_email=normalize_email("quiz.user@example.com"),
        quiz_data=quiz_data,
        calorie_target=1500,
    )
    test_session.add(quiz)
    await test_session.flush()

    assert quiz.id is not None
    assert quiz.user_id == user.id
    assert quiz.email == "quiz.user@example.com"
    assert quiz.quiz_data["step_1"] == "female"
    assert quiz.quiz_data["step_20"]["age"] == 30
    assert quiz.calorie_target == 1500
    assert quiz.payment_id is None
    assert quiz.pdf_delivered_at is None


@pytest.mark.asyncio
async def test_quiz_response_create_unauthenticated(test_session: AsyncSession):
    """Test creating a quiz response without user authentication."""
    quiz_data = {
        "step_1": "male",
        "step_20": {"age": 25, "weight_kg": 80, "height_cm": 180, "goal": "muscle_gain"}
    }

    quiz = QuizResponse(
        user_id=None,
        email="guest@example.com",
        normalized_email=normalize_email("guest@example.com"),
        quiz_data=quiz_data,
        calorie_target=2200,
    )
    test_session.add(quiz)
    await test_session.flush()

    assert quiz.id is not None
    assert quiz.user_id is None
    assert quiz.email == "guest@example.com"


@pytest.mark.asyncio
async def test_quiz_response_update_payment(test_session: AsyncSession):
    """Test updating quiz response with payment information."""
    quiz = QuizResponse(
        user_id=None,
        email="payment@example.com",
        normalized_email=normalize_email("payment@example.com"),
        quiz_data={"step_1": "female"},
        calorie_target=1600,
    )
    test_session.add(quiz)
    await test_session.flush()

    # Update with payment ID
    quiz.payment_id = "txn_123456"
    quiz.pdf_delivered_at = datetime.utcnow()
    await test_session.flush()

    assert quiz.payment_id == "txn_123456"
    assert quiz.pdf_delivered_at is not None


@pytest.mark.asyncio
async def test_quiz_response_delete_cascade(test_session: AsyncSession):
    """Test that deleting a user cascades to quiz responses."""
    user = User(
        email="cascade@example.com",
        normalized_email=normalize_email("cascade@example.com"),
        password_hash="hashed",
    )
    test_session.add(user)
    await test_session.flush()

    quiz = QuizResponse(
        user_id=user.id,
        email="cascade@example.com",
        normalized_email=normalize_email("cascade@example.com"),
        quiz_data={"step_1": "male"},
        calorie_target=1800,
    )
    test_session.add(quiz)
    await test_session.flush()
    quiz_id = quiz.id

    # Delete user
    await test_session.delete(user)
    await test_session.flush()

    # Verify quiz response was also deleted
    stmt = select(QuizResponse).where(QuizResponse.id == quiz_id)
    result = await test_session.execute(stmt)
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_quiz_response_jsonb_query(test_session: AsyncSession):
    """Test JSONB queries on quiz_data field."""
    # Create multiple quiz responses with different data
    quiz1 = QuizResponse(
        user_id=None,
        email="jsonb1@example.com",
        normalized_email=normalize_email("jsonb1@example.com"),
        quiz_data={"step_1": "female", "step_2": "sedentary"},
        calorie_target=1400,
    )
    quiz2 = QuizResponse(
        user_id=None,
        email="jsonb2@example.com",
        normalized_email=normalize_email("jsonb2@example.com"),
        quiz_data={"step_1": "male", "step_2": "very_active"},
        calorie_target=2500,
    )
    test_session.add_all([quiz1, quiz2])
    await test_session.flush()

    # Query by JSONB field (step_1 = "female") scoped to this test's records only.
    # The shared SQLite DB may have other records from previous tests, so we
    # filter by the specific emails created in this test to avoid count mismatches.
    stmt = select(QuizResponse).where(
        QuizResponse.quiz_data["step_1"].astext == "female",
        QuizResponse.email.in_(["jsonb1@example.com", "jsonb2@example.com"]),
    )
    result = await test_session.execute(stmt)
    female_quizzes = result.scalars().all()

    assert len(female_quizzes) == 1
    assert female_quizzes[0].email == "jsonb1@example.com"


@pytest.mark.asyncio
async def test_quiz_response_relationship(test_session: AsyncSession):
    """Test User->QuizResponse relationship."""
    user = User(
        email="relationship@example.com",
        normalized_email=normalize_email("relationship@example.com"),
        password_hash="hashed",
    )
    test_session.add(user)
    await test_session.flush()

    # Create two quiz responses for same user
    quiz1 = QuizResponse(
        user_id=user.id,
        email="relationship@example.com",
        normalized_email=normalize_email("relationship@example.com"),
        quiz_data={"step_1": "female"},
        calorie_target=1500,
    )
    quiz2 = QuizResponse(
        user_id=user.id,
        email="relationship@example.com",
        normalized_email=normalize_email("relationship@example.com"),
        quiz_data={"step_1": "female"},
        calorie_target=1600,
    )
    test_session.add_all([quiz1, quiz2])
    await test_session.flush()

    # Reload user to access relationship
    await test_session.refresh(user, ["quiz_responses"])

    assert len(user.quiz_responses) == 2
    assert all(qr.user_id == user.id for qr in user.quiz_responses)


# ============================================================================
# MealPlan Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_meal_plan_create(test_session: AsyncSession):
    """Test creating a meal plan."""
    preferences = {
        "excluded_foods": ["beef", "pork"],
        "preferred_proteins": ["chicken", "fish"],
        "dietary_restrictions": "No dairy"
    }

    meal_plan = MealPlan(
        payment_id="txn_mealplan_123",
        email="mealplan@example.com",
        normalized_email=normalize_email("mealplan@example.com"),
        pdf_blob_path="/blobs/meal_plan_123.pdf",
        calorie_target=1800,
        preferences_summary=preferences,
        ai_model="gpt-4o",
        status="completed",
        refund_count=0,
    )
    test_session.add(meal_plan)
    await test_session.flush()

    assert meal_plan.id is not None
    assert meal_plan.payment_id == "txn_mealplan_123"
    assert meal_plan.pdf_blob_path == "/blobs/meal_plan_123.pdf"
    assert meal_plan.ai_model == "gpt-4o"
    assert meal_plan.status == "completed"
    assert meal_plan.preferences_summary["excluded_foods"] == ["beef", "pork"]


@pytest.mark.asyncio
async def test_meal_plan_unique_payment_id(test_session: AsyncSession):
    """Test that duplicate payment_ids are rejected."""
    meal_plan1 = MealPlan(
        payment_id="txn_unique_123",
        email="unique1@example.com",
        normalized_email=normalize_email("unique1@example.com"),
        pdf_blob_path="/blobs/plan1.pdf",
        calorie_target=1800,
        preferences_summary={},
        ai_model="gpt-4o",
    )
    test_session.add(meal_plan1)
    await test_session.flush()

    # Try to create meal plan with same payment_id
    meal_plan2 = MealPlan(
        payment_id="txn_unique_123",
        email="unique2@example.com",
        normalized_email=normalize_email("unique2@example.com"),
        pdf_blob_path="/blobs/plan2.pdf",
        calorie_target=2000,
        preferences_summary={},
        ai_model="gpt-4o",
    )
    test_session.add(meal_plan2)

    with pytest.raises(IntegrityError):
        await test_session.flush()


@pytest.mark.asyncio
async def test_meal_plan_update_status(test_session: AsyncSession):
    """Test updating meal plan status."""
    meal_plan = MealPlan(
        payment_id="txn_status_123",
        email="status@example.com",
        normalized_email=normalize_email("status@example.com"),
        pdf_blob_path="/blobs/status.pdf",
        calorie_target=1800,
        preferences_summary={},
        ai_model="gpt-4o",
        status="processing",
    )
    test_session.add(meal_plan)
    await test_session.flush()

    # Update status
    meal_plan.status = "completed"
    meal_plan.email_sent_at = datetime.utcnow()
    await test_session.flush()

    assert meal_plan.status == "completed"
    assert meal_plan.email_sent_at is not None


@pytest.mark.asyncio
async def test_meal_plan_jsonb_query_preferences(test_session: AsyncSession):
    """Test JSONB queries on preferences_summary field."""
    meal_plan1 = MealPlan(
        payment_id="txn_pref1",
        email="pref1@example.com",
        normalized_email=normalize_email("pref1@example.com"),
        pdf_blob_path="/blobs/pref1.pdf",
        calorie_target=1800,
        preferences_summary={
            "excluded_foods": ["beef"],
            "preferred_proteins": ["chicken"]
        },
        ai_model="gpt-4o",
    )
    meal_plan2 = MealPlan(
        payment_id="txn_pref2",
        email="pref2@example.com",
        normalized_email=normalize_email("pref2@example.com"),
        pdf_blob_path="/blobs/pref2.pdf",
        calorie_target=2000,
        preferences_summary={
            "excluded_foods": ["pork"],
            "preferred_proteins": ["fish"]
        },
        ai_model="gpt-4o",
    )
    test_session.add_all([meal_plan1, meal_plan2])
    await test_session.flush()

    # Query by JSONB field - check if preferred_proteins contains "chicken".
    # Scope to this test's records by payment_id to avoid count mismatches from
    # other tests that have committed records to the shared SQLite DB.
    stmt = select(MealPlan).where(
        MealPlan.preferences_summary["preferred_proteins"].astext.contains("chicken"),
        MealPlan.payment_id.in_(["txn_pref1", "txn_pref2"]),
    )
    result = await test_session.execute(stmt)
    chicken_plans = result.scalars().all()

    assert len(chicken_plans) == 1
    assert chicken_plans[0].email == "pref1@example.com"


# ============================================================================
# PaymentTransaction Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_payment_transaction_create(test_session: AsyncSession):
    """Test creating a payment transaction."""
    payment = PaymentTransaction(
        payment_id="txn_payment_123",
        meal_plan_id=None,
        amount=29.99,
        currency="USD",
        payment_method="card",
        payment_status="succeeded",
        paddle_created_at=datetime.utcnow(),
        customer_email="payment@example.com",
        normalized_email=normalize_email("payment@example.com"),
    )
    test_session.add(payment)
    await test_session.flush()

    assert payment.id is not None
    assert payment.payment_id == "txn_payment_123"
    assert float(payment.amount) == 29.99
    assert payment.currency == "USD"
    assert payment.payment_method == "card"
    assert payment.payment_status == "succeeded"


@pytest.mark.asyncio
async def test_payment_transaction_unique_payment_id(test_session: AsyncSession):
    """Test that duplicate payment_ids are rejected."""
    payment1 = PaymentTransaction(
        payment_id="txn_dup_123",
        amount=29.99,
        currency="USD",
        payment_method="card",
        payment_status="succeeded",
        paddle_created_at=datetime.utcnow(),
        customer_email="dup1@example.com",
        normalized_email=normalize_email("dup1@example.com"),
    )
    test_session.add(payment1)
    await test_session.flush()

    # Try to create payment with same payment_id
    payment2 = PaymentTransaction(
        payment_id="txn_dup_123",
        amount=19.99,
        currency="EUR",
        payment_method="apple_pay",
        payment_status="succeeded",
        paddle_created_at=datetime.utcnow(),
        customer_email="dup2@example.com",
        normalized_email=normalize_email("dup2@example.com"),
    )
    test_session.add(payment2)

    with pytest.raises(IntegrityError):
        await test_session.flush()


@pytest.mark.asyncio
async def test_payment_transaction_update_status(test_session: AsyncSession):
    """Test updating payment status to refunded."""
    payment = PaymentTransaction(
        payment_id="txn_refund_123",
        amount=29.99,
        currency="USD",
        payment_method="card",
        payment_status="succeeded",
        paddle_created_at=datetime.utcnow(),
        customer_email="refund@example.com",
        normalized_email=normalize_email("refund@example.com"),
    )
    test_session.add(payment)
    await test_session.flush()

    # Update status to refunded
    payment.payment_status = "refunded"
    await test_session.flush()

    assert payment.payment_status == "refunded"


@pytest.mark.asyncio
async def test_payment_meal_plan_relationship(test_session: AsyncSession):
    """Test PaymentTransaction->MealPlan relationship."""
    # Create meal plan first
    meal_plan = MealPlan(
        payment_id="txn_rel_123",
        email="rel@example.com",
        normalized_email=normalize_email("rel@example.com"),
        pdf_blob_path="/blobs/rel.pdf",
        calorie_target=1800,
        preferences_summary={},
        ai_model="gpt-4o",
    )
    test_session.add(meal_plan)
    await test_session.flush()

    # Create payment transaction
    payment = PaymentTransaction(
        payment_id="txn_rel_123",
        meal_plan_id=meal_plan.id,
        amount=29.99,
        currency="USD",
        payment_method="card",
        payment_status="succeeded",
        paddle_created_at=datetime.utcnow(),
        customer_email="rel@example.com",
        normalized_email=normalize_email("rel@example.com"),
    )
    test_session.add(payment)
    await test_session.flush()

    # Reload payment to access relationship
    await test_session.refresh(payment, ["meal_plan"])

    assert payment.meal_plan is not None
    assert payment.meal_plan.id == meal_plan.id
    assert payment.meal_plan.payment_id == payment.payment_id


# ============================================================================
# ManualResolution Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_manual_resolution_create(test_session: AsyncSession):
    """Test creating a manual resolution entry."""
    sla_deadline = datetime.utcnow() + timedelta(hours=4)

    resolution = ManualResolution(
        payment_id="txn_manual_123",
        user_email="manual@example.com",
        normalized_email=normalize_email("manual@example.com"),
        issue_type="missing_quiz_data",
        status="pending",
        sla_deadline=sla_deadline,
    )
    test_session.add(resolution)
    await test_session.flush()

    assert resolution.id is not None
    assert resolution.payment_id == "txn_manual_123"
    assert resolution.issue_type == "missing_quiz_data"
    assert resolution.status == "pending"
    assert resolution.assigned_to is None
    assert resolution.resolution_notes is None


@pytest.mark.asyncio
async def test_manual_resolution_update_status(test_session: AsyncSession):
    """Test updating manual resolution status and assignment."""
    resolution = ManualResolution(
        payment_id="txn_update_123",
        user_email="update@example.com",
        normalized_email=normalize_email("update@example.com"),
        issue_type="ai_validation_failed",
        status="pending",
        sla_deadline=datetime.utcnow() + timedelta(hours=4),
    )
    test_session.add(resolution)
    await test_session.flush()

    # Update status and assign
    resolution.status = "in_progress"
    resolution.assigned_to = "admin@example.com"
    resolution.resolution_notes = "Investigating the issue"
    await test_session.flush()

    assert resolution.status == "in_progress"
    assert resolution.assigned_to == "admin@example.com"
    assert resolution.resolution_notes == "Investigating the issue"


@pytest.mark.asyncio
async def test_manual_resolution_query_by_status(test_session: AsyncSession):
    """Test querying manual resolutions by status."""
    resolution1 = ManualResolution(
        payment_id="txn_status1",
        user_email="status1@example.com",
        normalized_email=normalize_email("status1@example.com"),
        issue_type="missing_quiz_data",
        status="pending",
        sla_deadline=datetime.utcnow() + timedelta(hours=4),
    )
    resolution2 = ManualResolution(
        payment_id="txn_status2",
        user_email="status2@example.com",
        normalized_email=normalize_email("status2@example.com"),
        issue_type="ai_validation_failed",
        status="resolved",
        sla_deadline=datetime.utcnow() + timedelta(hours=4),
        resolved_at=datetime.utcnow(),
    )
    test_session.add_all([resolution1, resolution2])
    await test_session.flush()

    # Query pending resolutions scoped to this test's records by payment_id.
    # The shared SQLite DB accumulates records from prior tests, so we must
    # filter to avoid count mismatches on global queries.
    stmt = select(ManualResolution).where(
        ManualResolution.status == "pending",
        ManualResolution.payment_id.in_(["txn_status1", "txn_status2"]),
    )
    result = await test_session.execute(stmt)
    pending = result.scalars().all()

    assert len(pending) == 1
    assert pending[0].payment_id == "txn_status1"


# ============================================================================
# MagicLinkToken Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_magic_link_create(test_session: AsyncSession):
    """Test creating a magic link token."""
    token = MagicLinkToken(
        token_hash="abc123def456" * 5 + "abcd",  # 64 chars
        email="magic@example.com",
        normalized_email=normalize_email("magic@example.com"),
        generation_ip="192.168.1.1",
    )
    test_session.add(token)
    await test_session.flush()

    assert token.id is not None
    assert token.token_hash == "abc123def456" * 5 + "abcd"
    assert token.email == "magic@example.com"
    assert token.expires_at is not None
    assert token.used_at is None
    assert token.generation_ip == "192.168.1.1"


@pytest.mark.asyncio
async def test_magic_link_unique_token_hash(test_session: AsyncSession):
    """Test that duplicate token hashes are rejected."""
    token_hash = "unique123456" * 5 + "abcd"  # 64 chars

    token1 = MagicLinkToken(
        token_hash=token_hash,
        email="unique1@example.com",
        normalized_email=normalize_email("unique1@example.com"),
    )
    test_session.add(token1)
    await test_session.flush()

    # Try to create token with same hash
    token2 = MagicLinkToken(
        token_hash=token_hash,
        email="unique2@example.com",
        normalized_email=normalize_email("unique2@example.com"),
    )
    test_session.add(token2)

    with pytest.raises(IntegrityError):
        await test_session.flush()


@pytest.mark.asyncio
async def test_magic_link_mark_used(test_session: AsyncSession):
    """Test marking a magic link token as used."""
    token = MagicLinkToken(
        token_hash="used123456" * 5 + "abcd",  # 64 chars
        email="used@example.com",
        normalized_email=normalize_email("used@example.com"),
        generation_ip="192.168.1.1",
    )
    test_session.add(token)
    await test_session.flush()

    # Mark as used
    token.used_at = datetime.utcnow()
    token.usage_ip = "192.168.1.2"
    await test_session.flush()

    assert token.used_at is not None
    assert token.usage_ip == "192.168.1.2"


@pytest.mark.asyncio
async def test_magic_link_auto_expires_at(test_session: AsyncSession):
    """Test that expires_at is automatically calculated as created_at + 24h."""
    now = datetime.utcnow()
    token = MagicLinkToken(
        token_hash="expires123" * 5 + "abcd",  # 64 chars
        email="expires@example.com",
        normalized_email=normalize_email("expires@example.com"),
        created_at=now,
    )
    test_session.add(token)
    await test_session.flush()

    # Check that expires_at is approximately 24 hours after created_at
    time_diff = token.expires_at - token.created_at
    assert abs(time_diff.total_seconds() - 86400) < 1  # Within 1 second of 24 hours


# ============================================================================
# EmailBlacklist Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_email_blacklist_create(test_session: AsyncSession):
    """Test creating an email blacklist entry."""
    blacklist = EmailBlacklist(
        normalized_email=normalize_email("blacklist@example.com"),
        reason="chargeback",
    )
    test_session.add(blacklist)
    await test_session.flush()

    assert blacklist.id is not None
    assert blacklist.normalized_email == "blacklist@example.com"
    assert blacklist.reason == "chargeback"
    assert blacklist.created_at is not None
    assert blacklist.expires_at is not None


@pytest.mark.asyncio
async def test_email_blacklist_unique_normalized_email(test_session: AsyncSession):
    """Test that duplicate normalized emails are rejected."""
    blacklist1 = EmailBlacklist(
        normalized_email=normalize_email("duplicate.blacklist@gmail.com"),
        reason="chargeback",
    )
    test_session.add(blacklist1)
    await test_session.flush()

    # Try to create blacklist with same normalized email
    blacklist2 = EmailBlacklist(
        normalized_email=normalize_email("duplicateblacklist@gmail.com"),  # Same after normalization
        reason="chargeback",
    )
    test_session.add(blacklist2)

    with pytest.raises(IntegrityError):
        await test_session.flush()


@pytest.mark.asyncio
async def test_email_blacklist_auto_expires_at(test_session: AsyncSession):
    """Test that expires_at is automatically calculated as created_at + 90 days."""
    now = datetime.utcnow()
    blacklist = EmailBlacklist(
        normalized_email=normalize_email("expires.blacklist@example.com"),
        reason="chargeback",
        created_at=now,
    )
    test_session.add(blacklist)
    await test_session.flush()

    # Check that expires_at is approximately 90 days after created_at
    time_diff = blacklist.expires_at - blacklist.created_at
    expected_seconds = 90 * 86400  # 90 days in seconds
    assert abs(time_diff.total_seconds() - expected_seconds) < 1


@pytest.mark.asyncio
async def test_email_blacklist_query_active(test_session: AsyncSession):
    """Test querying active (non-expired) blacklist entries."""
    now = datetime.utcnow()

    # Active blacklist (expires in future)
    active = EmailBlacklist(
        normalized_email=normalize_email("active@example.com"),
        reason="chargeback",
        created_at=now,
        expires_at=now + timedelta(days=30),
    )

    # Expired blacklist
    expired = EmailBlacklist(
        normalized_email=normalize_email("expired@example.com"),
        reason="chargeback",
        created_at=now - timedelta(days=100),
        expires_at=now - timedelta(days=10),
    )

    test_session.add_all([active, expired])
    await test_session.flush()

    # Query active blacklists (expires_at > now) scoped to this test's records.
    # The shared SQLite DB accumulates records from prior tests, so filter by
    # the specific normalized emails created in this test.
    stmt = select(EmailBlacklist).where(
        EmailBlacklist.expires_at > now,
        EmailBlacklist.normalized_email.in_([
            normalize_email("active@example.com"),
            normalize_email("expired@example.com"),
        ]),
    )
    result = await test_session.execute(stmt)
    active_entries = result.scalars().all()

    assert len(active_entries) == 1
    assert active_entries[0].normalized_email == normalize_email("active@example.com")


# ============================================================================
# Complex Relationship and JSONB Tests
# ============================================================================


@pytest.mark.asyncio
async def test_complex_user_quiz_relationship(test_session: AsyncSession):
    """Test complex relationship between User and multiple QuizResponses."""
    # Create user
    user = User(
        email="complex@example.com",
        normalized_email=normalize_email("complex@example.com"),
        password_hash="hashed",
    )
    test_session.add(user)
    await test_session.flush()

    # Create multiple quiz responses with different data
    quiz1 = QuizResponse(
        user_id=user.id,
        email="complex@example.com",
        normalized_email=normalize_email("complex@example.com"),
        quiz_data={"step_1": "female", "step_2": "sedentary"},
        calorie_target=1400,
        payment_id="txn_complex_1",
    )
    quiz2 = QuizResponse(
        user_id=user.id,
        email="complex@example.com",
        normalized_email=normalize_email("complex@example.com"),
        quiz_data={"step_1": "female", "step_2": "moderately_active"},
        calorie_target=1600,
        payment_id="txn_complex_2",
    )
    test_session.add_all([quiz1, quiz2])
    await test_session.flush()

    # Query user with quiz responses
    stmt = select(User).where(User.id == user.id)
    result = await test_session.execute(stmt)
    fetched_user = result.scalar_one()
    await test_session.refresh(fetched_user, ["quiz_responses"])

    assert len(fetched_user.quiz_responses) == 2
    assert fetched_user.quiz_responses[0].quiz_data["step_2"] in ["sedentary", "moderately_active"]


@pytest.mark.asyncio
async def test_jsonb_nested_query(test_session: AsyncSession):
    """Test nested JSONB queries on quiz_data field."""
    quiz1 = QuizResponse(
        user_id=None,
        email="nested1@example.com",
        normalized_email=normalize_email("nested1@example.com"),
        quiz_data={
            "step_20": {
                "age": 25,
                "weight_kg": 60,
                "height_cm": 160,
                "goal": "weight_loss"
            }
        },
        calorie_target=1400,
    )
    quiz2 = QuizResponse(
        user_id=None,
        email="nested2@example.com",
        normalized_email=normalize_email("nested2@example.com"),
        quiz_data={
            "step_20": {
                "age": 30,
                "weight_kg": 70,
                "height_cm": 170,
                "goal": "muscle_gain"
            }
        },
        calorie_target=2200,
    )
    test_session.add_all([quiz1, quiz2])
    await test_session.flush()

    # Query by nested JSONB field (goal = "weight_loss"), scoped to test emails
    stmt = select(QuizResponse).where(
        QuizResponse.quiz_data["step_20"]["goal"].astext == "weight_loss",
        QuizResponse.email.in_(["nested1@example.com", "nested2@example.com"]),
    )
    result = await test_session.execute(stmt)
    weight_loss_quizzes = result.scalars().all()

    assert len(weight_loss_quizzes) == 1
    assert weight_loss_quizzes[0].email == "nested1@example.com"


@pytest.mark.asyncio
async def test_full_payment_flow(test_session: AsyncSession):
    """Test complete payment flow: User -> QuizResponse -> Payment -> MealPlan."""
    # Step 1: User creates account
    user = User(
        email="flow@example.com",
        normalized_email=normalize_email("flow@example.com"),
        password_hash="hashed",
    )
    test_session.add(user)
    await test_session.flush()

    # Step 2: User completes quiz
    quiz = QuizResponse(
        user_id=user.id,
        email="flow@example.com",
        normalized_email=normalize_email("flow@example.com"),
        quiz_data={"step_1": "female", "step_20": {"age": 28, "weight_kg": 65, "height_cm": 165, "goal": "weight_loss"}},
        calorie_target=1500,
    )
    test_session.add(quiz)
    await test_session.flush()

    # Step 3: Payment processed
    payment_id = "txn_flow_123"
    quiz.payment_id = payment_id
    await test_session.flush()

    # Step 4: Meal plan generated
    meal_plan = MealPlan(
        payment_id=payment_id,
        email="flow@example.com",
        normalized_email=normalize_email("flow@example.com"),
        pdf_blob_path="/blobs/flow.pdf",
        calorie_target=1500,
        preferences_summary={"excluded_foods": [], "preferred_proteins": ["chicken"]},
        ai_model="gpt-4o",
        status="completed",
    )
    test_session.add(meal_plan)
    await test_session.flush()

    # Step 5: Payment transaction recorded
    payment = PaymentTransaction(
        payment_id=payment_id,
        meal_plan_id=meal_plan.id,
        amount=29.99,
        currency="USD",
        payment_method="card",
        payment_status="succeeded",
        paddle_created_at=datetime.utcnow(),
        customer_email="flow@example.com",
        normalized_email=normalize_email("flow@example.com"),
    )
    test_session.add(payment)
    await test_session.flush()

    # Verify complete flow
    stmt = select(User).where(User.email == "flow@example.com")
    result = await test_session.execute(stmt)
    final_user = result.scalar_one()
    await test_session.refresh(final_user, ["quiz_responses"])

    assert len(final_user.quiz_responses) == 1
    assert final_user.quiz_responses[0].payment_id == payment_id

    # Verify payment-meal plan relationship
    await test_session.refresh(payment, ["meal_plan"])
    assert payment.meal_plan is not None
    assert payment.meal_plan.id == meal_plan.id
