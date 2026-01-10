#!/usr/bin/env python3
"""
QuizResponse Model Verification Test

Comprehensive test to verify the QuizResponse model implementation:
- Table structure and columns
- Indexes and foreign keys
- Relationships with User model
- Type hints and JSONB support
- Model instantiation with complete quiz data
"""

from src.models import QuizResponse, User
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from datetime import datetime


def test_table_structure():
    """Verify table name and column definitions."""
    print("Testing table structure...")

    assert QuizResponse.__tablename__ == "quiz_responses"

    columns = {col.name: col for col in QuizResponse.__table__.columns}

    # Verify all required columns exist
    required_columns = [
        "id", "user_id", "email", "normalized_email",
        "quiz_data", "calorie_target", "created_at",
        "payment_id", "pdf_delivered_at"
    ]
    for col_name in required_columns:
        assert col_name in columns, f"Missing column: {col_name}"

    # Verify column types
    assert isinstance(columns["quiz_data"].type, JSONB)
    assert columns["id"].primary_key
    assert columns["user_id"].nullable
    assert not columns["email"].nullable
    assert not columns["normalized_email"].nullable
    assert not columns["quiz_data"].nullable
    assert not columns["calorie_target"].nullable
    assert columns["payment_id"].nullable
    assert columns["pdf_delivered_at"].nullable

    print("✓ Table structure verified")


def test_indexes():
    """Verify all required indexes are created."""
    print("\nTesting indexes...")

    indexes = {idx.name: idx for idx in QuizResponse.__table__.indexes}

    required_indexes = [
        "idx_quiz_normalized_email",
        "idx_quiz_created_at",
        "idx_quiz_pdf_delivered_at"
    ]

    for idx_name in required_indexes:
        assert idx_name in indexes, f"Missing index: {idx_name}"

    # Verify index columns
    assert "normalized_email" in [col.name for col in indexes["idx_quiz_normalized_email"].columns]
    assert "created_at" in [col.name for col in indexes["idx_quiz_created_at"].columns]
    assert "pdf_delivered_at" in [col.name for col in indexes["idx_quiz_pdf_delivered_at"].columns]

    print("✓ All indexes verified")


def test_foreign_keys():
    """Verify foreign key constraints."""
    print("\nTesting foreign keys...")

    fks = list(QuizResponse.__table__.foreign_keys)

    assert len(fks) == 1
    assert fks[0].parent.name == "user_id"
    assert fks[0].target_fullname == "users.id"
    assert fks[0].ondelete == "CASCADE"

    print("✓ Foreign key constraints verified")


def test_relationships():
    """Verify bidirectional relationship with User model."""
    print("\nTesting relationships...")

    # Test QuizResponse -> User relationship
    quiz_rel = QuizResponse.__mapper__.relationships.get("user")
    assert quiz_rel is not None
    assert quiz_rel.mapper.class_.__name__ == "User"
    assert quiz_rel.back_populates == "quiz_responses"
    assert quiz_rel.lazy == "joined"

    # Test User -> QuizResponse relationship
    user_rel = User.__mapper__.relationships.get("quiz_responses")
    assert user_rel is not None
    assert user_rel.mapper.class_.__name__ == "QuizResponse"
    assert user_rel.back_populates == "user"
    assert "delete-orphan" in str(user_rel.cascade)

    print("✓ Bidirectional relationships verified")


def test_model_instantiation():
    """Test creating QuizResponse instances with complete data."""
    print("\nTesting model instantiation...")

    # Complete quiz data matching spec
    quiz_data = {
        "step_1": "female",
        "step_2": "moderately_active",
        "step_3": ["chicken", "turkey"],
        "step_4": ["salmon", "tuna"],
        "step_5": ["avocado", "zucchini", "bell_pepper"],
        "step_6": ["broccoli", "cauliflower"],
        "step_7": ["spinach", "arugula"],
        "step_8": [],
        "step_9": ["shrimp"],
        "step_10": [],
        "step_11": ["blueberries", "strawberries"],
        "step_12": [],
        "step_13": [],
        "step_14": ["olive_oil", "coconut_oil", "butter"],
        "step_15": ["water", "coffee", "tea"],
        "step_16": ["cheese", "greek_yogurt"],
        "step_17": "No dairy from cows, goat dairy OK. Prefer coconut-based alternatives.",
        "step_18": "3_meals",
        "step_19": ["prefer_salty", "struggle_appetite_control"],
        "step_20": {
            "age": 35,
            "weight_kg": 65,
            "height_cm": 165,
            "goal": "weight_loss"
        }
    }

    # Test unauthenticated flow (user_id = None)
    quiz1 = QuizResponse(
        id=str(uuid.uuid4()),
        user_id=None,
        email="guest@example.com",
        normalized_email="guest@example.com",
        quiz_data=quiz_data,
        calorie_target=1500,
        created_at=datetime.utcnow()
    )

    assert quiz1.user_id is None
    assert quiz1.email == "guest@example.com"
    assert quiz1.calorie_target == 1500
    assert quiz1.payment_id is None
    assert quiz1.pdf_delivered_at is None
    assert len(quiz1.quiz_data) == 20

    # Test authenticated flow (with user_id)
    user_id = str(uuid.uuid4())
    quiz2 = QuizResponse(
        id=str(uuid.uuid4()),
        user_id=user_id,
        email="user@example.com",
        normalized_email="user@example.com",
        quiz_data=quiz_data,
        calorie_target=1800,
        created_at=datetime.utcnow(),
        payment_id="pay_12345",
        pdf_delivered_at=datetime.utcnow()
    )

    assert quiz2.user_id == user_id
    assert quiz2.payment_id == "pay_12345"
    assert quiz2.pdf_delivered_at is not None

    print("✓ Model instantiation verified (authenticated & unauthenticated)")


def test_repr_method():
    """Test __repr__ output for debugging."""
    print("\nTesting __repr__ method...")

    quiz = QuizResponse(
        id="test-uuid-123",
        email="test@example.com",
        normalized_email="test@example.com",
        quiz_data={"step_1": "female"},
        calorie_target=1500,
        created_at=datetime(2026, 1, 6, 12, 0, 0)
    )

    repr_str = repr(quiz)
    assert "QuizResponse" in repr_str
    assert "test-uuid-123" in repr_str
    assert "test@example.com" in repr_str

    print(f"  Sample repr: {repr_str}")
    print("✓ __repr__ method verified")


if __name__ == "__main__":
    print("=" * 70)
    print("QuizResponse Model Comprehensive Verification")
    print("=" * 70)

    test_table_structure()
    test_indexes()
    test_foreign_keys()
    test_relationships()
    test_model_instantiation()
    test_repr_method()

    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED - QuizResponse model is production-ready")
    print("=" * 70)
