# Data Model: Keto Meal Plan Generator

**Feature Branch**: `001-keto-meal-plan-generator`
**Date**: 2025-12-30
**Spec**: [spec.md](./spec.md)
**Phase**: 1 - Design

---

## Database Schema

### Technology
- **Database**: Neon DB (Serverless PostgreSQL 15+)
- **ORM**: SQLAlchemy 2.0+ (async)
- **Migrations**: Alembic

---

## Entity Relationship Diagram

```
┌─────────────────┐
│     User        │
├─────────────────┤
│ id (PK)         │
│ email           │
│ password_hash   │──┐
│ created_at      │  │
│ updated_at      │  │
└─────────────────┘  │
                     │
                     │ 1:N
                     │
┌─────────────────┐  │
│  QuizResponse   │  │
├─────────────────┤  │
│ id (PK)         │  │
│ user_id (FK)    │──┘ (nullable - supports unauthenticated flow)
│ email           │
│ normalized_email│
│ quiz_data (JSONB)│
│ calorie_target  │
│ created_at      │
│ pdf_delivered_at│
└─────────────────┘
         │
         │ 1:1
         │
┌─────────────────┐
│   MealPlan      │
├─────────────────┤
│ id (PK)         │
│ payment_id (UQ) │
│ email           │
│ normalized_email│
│ pdf_blob_url    │
│ calorie_target  │
│ preferences_summary (JSONB)│
│ ai_model        │
│ status          │
│ refund_count    │
│ created_at      │
│ email_sent_at   │
└─────────────────┘
         │
         │ 1:1
         │
┌──────────────────────┐
│ PaymentTransaction   │
├──────────────────────┤
│ id (PK)              │
│ payment_id (UQ)      │
│ meal_plan_id (FK)    │──┘ (nullable initially)
│ amount               │
│ currency             │
│ payment_method       │
│ payment_status       │
│ paddle_created_at    │
│ webhook_received_at  │
│ customer_email       │
│ normalized_email     │
│ created_at           │
│ updated_at           │
└──────────────────────┘

┌─────────────────────┐
│ ManualResolution    │
├─────────────────────┤
│ id (PK)             │
│ payment_id          │
│ user_email          │
│ normalized_email    │
│ issue_type          │
│ status              │
│ sla_deadline        │
│ created_at          │
│ resolved_at         │
│ assigned_to         │
│ resolution_notes    │
└─────────────────────┘

┌─────────────────────┐
│ MagicLinkToken      │
├─────────────────────┤
│ id (PK)             │
│ token_hash (UQ)     │
│ email               │
│ normalized_email    │
│ created_at          │
│ expires_at          │
│ used_at             │
│ generation_ip       │
│ usage_ip            │
└─────────────────────┘

┌─────────────────────┐
│ EmailBlacklist      │
├─────────────────────┤
│ id (PK)             │
│ normalized_email(UQ)│
│ reason              │
│ created_at          │
│ expires_at          │
└─────────────────────┘
```

---

## Entities

### 1. User (Optional Account)

**Purpose**: Stores optional user accounts for dashboard access and cross-device quiz sync.

**Columns**:
- `id` (UUID, PK): Unique user identifier
- `email` (VARCHAR(255), UNIQUE, NOT NULL): Original email (for communications)
- `normalized_email` (VARCHAR(255), INDEXED, NOT NULL): Normalized email (for lookups, Gmail alias prevention)
- `password_hash` (VARCHAR(255), NULLABLE): Bcrypt hash (NULL if account created via magic link)
- `created_at` (TIMESTAMP, NOT NULL): Account creation timestamp
- `updated_at` (TIMESTAMP, NOT NULL): Last update timestamp

**Indexes**:
- `idx_user_email`: `email` (unique)
- `idx_user_normalized_email`: `normalized_email`

**Retention**: Indefinite (until user deletion request or GDPR compliance)

**SQLAlchemy Model**:
```python
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    normalized_email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # NULL for magic link accounts
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_user_email", "email", unique=True),
        Index("idx_user_normalized_email", "normalized_email"),
    )
```

---

### 2. QuizResponse

**Purpose**: Temporary storage of 20-step quiz answers. Supports both authenticated (user_id populated) and unauthenticated (user_id NULL) flows.

**Columns**:
- `id` (UUID, PK): Unique quiz response identifier
- `user_id` (UUID, FK, NULLABLE): References `users.id` (NULL for unauthenticated users)
- `email` (VARCHAR(255), NOT NULL): Original email
- `normalized_email` (VARCHAR(255), INDEXED, NOT NULL): Normalized email
- `quiz_data` (JSONB, NOT NULL): Full 20-step quiz responses (structure below)
- `calorie_target` (INTEGER, NOT NULL): Calculated calorie target (Mifflin-St Jeor)
- `created_at` (TIMESTAMP, NOT NULL): Quiz submission timestamp
- `payment_id` (VARCHAR(255), NULLABLE): Paddle payment ID (NULL until payment webhook)
- `pdf_delivered_at` (TIMESTAMP, NULLABLE): PDF email delivery timestamp

**Indexes**:
- `idx_quiz_normalized_email`: `normalized_email`
- `idx_quiz_created_at`: `created_at` (for cleanup job)
- `idx_quiz_pdf_delivered_at`: `pdf_delivered_at` (for 24h deletion)

**Retention**:
- **Paid (payment_id NOT NULL)**: Deleted 24 hours after `pdf_delivered_at`
- **Unpaid (payment_id NULL)**: Deleted 7 days after `created_at`

**quiz_data JSONB Structure**:
```json
{
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
```

**SQLAlchemy Model**:
```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

class QuizResponse(Base):
    __tablename__ = "quiz_responses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # NULL for unauthenticated
    email = Column(String(255), nullable=False)
    normalized_email = Column(String(255), nullable=False, index=True)
    quiz_data = Column(JSONB, nullable=False)
    calorie_target = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    payment_id = Column(String(255), nullable=True)
    pdf_delivered_at = Column(DateTime, nullable=True, index=True)

    __table_args__ = (
        Index("idx_quiz_normalized_email", "normalized_email"),
        Index("idx_quiz_created_at", "created_at"),
        Index("idx_quiz_pdf_delivered_at", "pdf_delivered_at"),
    )
```

---

### 3. MealPlan

**Purpose**: Stores meal plan metadata, payment reference, PDF URL, and food preference summary (retained 90 days).

**Columns**:
- `id` (UUID, PK): Unique meal plan identifier
- `payment_id` (VARCHAR(255), UNIQUE, NOT NULL): Paddle payment transaction ID
- `email` (VARCHAR(255), NOT NULL): Original email
- `normalized_email` (VARCHAR(255), INDEXED, NOT NULL): Normalized email
- `pdf_blob_url` (TEXT, NOT NULL): Vercel Blob signed URL
- `calorie_target` (INTEGER, NOT NULL): Daily calorie target
- `preferences_summary` (JSONB, NOT NULL): Derived food preferences (structure below)
- `ai_model` (VARCHAR(50), NOT NULL): Model used (gpt-4o, gemini-1.5-pro)
- `status` (VARCHAR(50), NOT NULL): processing, completed, failed, refunded
- `refund_count` (INTEGER, DEFAULT 0): Number of refunds for abuse prevention (FR-P-011)
- `created_at` (TIMESTAMP, NOT NULL, INDEXED): Meal plan creation timestamp
- `email_sent_at` (TIMESTAMP, NULLABLE): Email delivery timestamp

**Indexes**:
- `idx_mealplan_payment_id`: `payment_id` (unique)
- `idx_mealplan_normalized_email`: `normalized_email`
- `idx_mealplan_created_at`: `created_at` (for 90-day cleanup)

**Retention**: 90 days (deleted via scheduled job)

**preferences_summary JSONB Structure** (FR-A-014):
```json
{
  "excluded_foods": ["beef", "pork", "lamb", "chickpeas", "lentils", "rice", "pasta", "bread"],
  "preferred_proteins": ["chicken", "turkey", "salmon", "tuna", "shrimp"],
  "dietary_restrictions": "No dairy from cows, goat dairy OK. Prefer coconut-based alternatives."
}
```

**SQLAlchemy Model**:
```python
class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), nullable=False)
    normalized_email = Column(String(255), nullable=False, index=True)
    pdf_blob_url = Column(Text, nullable=False)
    calorie_target = Column(Integer, nullable=False)
    preferences_summary = Column(JSONB, nullable=False)
    ai_model = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="processing")
    refund_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    email_sent_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_mealplan_payment_id", "payment_id", unique=True),
        Index("idx_mealplan_normalized_email", "normalized_email"),
        Index("idx_mealplan_created_at", "created_at"),
    )
```

---

### 4. ManualResolution

**Purpose**: Queue for failed operations requiring manual intervention (FR-M-001 to FR-M-006).

**Columns**:
- `id` (UUID, PK): Unique queue entry identifier
- `payment_id` (VARCHAR(255), NOT NULL): Paddle payment ID
- `user_email` (VARCHAR(255), NOT NULL): Original user email
- `normalized_email` (VARCHAR(255), INDEXED, NOT NULL): Normalized email
- `issue_type` (VARCHAR(50), NOT NULL): Enum: missing_quiz_data, ai_validation_failed, email_delivery_failed, manual_refund_required
- `status` (VARCHAR(50), NOT NULL): Enum: pending, in_progress, resolved, escalated, sla_missed_refunded
- `sla_deadline` (TIMESTAMP, NOT NULL, INDEXED): created_at + 4 hours
- `created_at` (TIMESTAMP, NOT NULL): Queue entry creation timestamp
- `resolved_at` (TIMESTAMP, NULLABLE): Resolution timestamp
- `assigned_to` (VARCHAR(255), NULLABLE): Admin user assigned
- `resolution_notes` (TEXT, NULLABLE): Admin notes

**Indexes**:
- `idx_manual_sla_deadline`: `sla_deadline` (for SLA breach checks)
- `idx_manual_status`: `status`
- `idx_manual_created_at`: `created_at` (for 1-year cleanup)

**Retention**: 1 year (compliance audit)

**SQLAlchemy Model**:
```python
from sqlalchemy import Text

class ManualResolution(Base):
    __tablename__ = "manual_resolution"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = Column(String(255), nullable=False)
    user_email = Column(String(255), nullable=False)
    normalized_email = Column(String(255), nullable=False, index=True)
    issue_type = Column(String(50), nullable=False)  # missing_quiz_data, ai_validation_failed, etc.
    status = Column(String(50), nullable=False, default="pending")  # pending, in_progress, resolved, etc.
    sla_deadline = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    assigned_to = Column(String(255), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_manual_sla_deadline", "sla_deadline"),
        Index("idx_manual_status", "status"),
        Index("idx_manual_created_at", "created_at"),
    )
```

---

### 5. MagicLinkToken

**Purpose**: Secure tokens for password-less PDF recovery (FR-R-002).

**Columns**:
- `id` (UUID, PK): Unique token identifier
- `token_hash` (VARCHAR(64), UNIQUE, NOT NULL): SHA256 hash of 256-bit token
- `email` (VARCHAR(255), NOT NULL): Original email
- `normalized_email` (VARCHAR(255), INDEXED, NOT NULL): Normalized email
- `created_at` (TIMESTAMP, NOT NULL): Token generation timestamp
- `expires_at` (TIMESTAMP, NOT NULL, INDEXED): created_at + 24 hours
- `used_at` (TIMESTAMP, NULLABLE): First use timestamp (single-use enforcement)
- `generation_ip` (VARCHAR(45), NULLABLE): IP address where token was generated
- `usage_ip` (VARCHAR(45), NULLABLE): IP address where token was used

**Indexes**:
- `idx_magic_token_hash`: `token_hash` (unique)
- `idx_magic_expires_at`: `expires_at` (for cleanup job)

**Retention**: Deleted after expiration (24h)

**SQLAlchemy Model**:
```python
class MagicLinkToken(Base):
    __tablename__ = "magic_link_tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    token_hash = Column(String(64), unique=True, nullable=False)
    email = Column(String(255), nullable=False)
    normalized_email = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    generation_ip = Column(String(45), nullable=True)
    usage_ip = Column(String(45), nullable=True)

    __table_args__ = (
        Index("idx_magic_token_hash", "token_hash", unique=True),
        Index("idx_magic_expires_at", "expires_at"),
    )
```

---

### 6. EmailBlacklist

**Purpose**: Prevent re-purchase by users with chargebacks (FR-P-009).

**Columns**:
- `id` (UUID, PK): Unique blacklist entry identifier
- `normalized_email` (VARCHAR(255), UNIQUE, NOT NULL): Normalized email
- `reason` (VARCHAR(50), NOT NULL): "chargeback"
- `created_at` (TIMESTAMP, NOT NULL): Blacklist creation timestamp
- `expires_at` (TIMESTAMP, NOT NULL, INDEXED): created_at + 90 days

**Indexes**:
- `idx_blacklist_normalized_email`: `normalized_email` (unique)
- `idx_blacklist_expires_at`: `expires_at` (for cleanup job)

**Retention**: 90 days (auto-deleted via scheduled job)

**SQLAlchemy Model**:
```python
class EmailBlacklist(Base):
    __tablename__ = "email_blacklist"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    normalized_email = Column(String(255), unique=True, nullable=False)
    reason = Column(String(50), nullable=False)  # "chargeback"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)

    __table_args__ = (
        Index("idx_blacklist_normalized_email", "normalized_email", unique=True),
        Index("idx_blacklist_expires_at", "expires_at"),
    )
```

---

### 7. PaymentTransaction

**Purpose**: Store payment transaction metadata for analytics, customer support, compliance, and fraud detection (FR-P-013).

**Columns**:
- `id` (UUID, PK): Unique payment transaction identifier
- `payment_id` (VARCHAR(255), UNIQUE, NOT NULL): Paddle transaction ID
- `meal_plan_id` (UUID, FK, NULLABLE): References `meal_plans.id` (NULL until meal plan created)
- `amount` (DECIMAL(10,2), NOT NULL): Payment amount (e.g., 29.99)
- `currency` (VARCHAR(3), NOT NULL): ISO currency code (USD, EUR, GBP)
- `payment_method` (VARCHAR(50), NOT NULL): Payment method type (card, apple_pay, google_pay, ideal, alipay, bank_transfer)
- `payment_status` (VARCHAR(50), NOT NULL): Transaction status (succeeded, refunded, chargeback)
- `paddle_created_at` (TIMESTAMP, NOT NULL): Payment timestamp from Paddle
- `webhook_received_at` (TIMESTAMP, NOT NULL): System timestamp when webhook was processed
- `customer_email` (VARCHAR(255), NOT NULL): Original customer email
- `normalized_email` (VARCHAR(255), INDEXED, NOT NULL): Normalized email (per FR-P-010)
- `created_at` (TIMESTAMP, NOT NULL): Record creation timestamp
- `updated_at` (TIMESTAMP, NOT NULL): Record update timestamp

**Indexes**:
- `idx_payment_transaction_id`: `payment_id` (unique)
- `idx_payment_normalized_email`: `normalized_email`
- `idx_payment_paddle_created_at`: `paddle_created_at` (for analytics queries)
- `idx_payment_status`: `payment_status` (for refund/chargeback queries)

**Retention**: 1 year (for compliance/audit, matching FR-M-006)

**Use Cases**:
- **Analytics**: Revenue tracking by payment method, currency distribution, daily/monthly reports
- **Customer Support**: Quick payment lookup without Paddle API calls
- **Fraud Detection**: Multiple payment patterns, abuse prevention (FR-P-011)
- **Compliance**: Financial records for tax/accounting, chargeback dispute evidence

**Security Notes**:
- NEVER stores PCI-sensitive data (card numbers, CVV, expiration dates, billing addresses)
- Only stores safe transaction metadata provided by Paddle webhook
- Complies with PCI-DSS by not handling payment instrument data

**SQLAlchemy Model**:
```python
from sqlalchemy import DECIMAL

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = Column(String(255), unique=True, nullable=False)
    meal_plan_id = Column(String, ForeignKey("meal_plans.id"), nullable=True)  # NULL until meal plan created
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)  # USD, EUR, GBP
    payment_method = Column(String(50), nullable=False)  # card, apple_pay, google_pay, etc.
    payment_status = Column(String(50), nullable=False, default="succeeded")  # succeeded, refunded, chargeback
    paddle_created_at = Column(DateTime, nullable=False)
    webhook_received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    customer_email = Column(String(255), nullable=False)
    normalized_email = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_payment_transaction_id", "payment_id", unique=True),
        Index("idx_payment_normalized_email", "normalized_email"),
        Index("idx_payment_paddle_created_at", "paddle_created_at"),
        Index("idx_payment_status", "payment_status"),
    )
```

---

## Data Retention Summary

| Entity | Retention Period | Deletion Trigger | Cleanup Job Frequency |
|--------|------------------|------------------|-----------------------|
| `quiz_responses` (paid) | 24 hours | `pdf_delivered_at` + 24h | Every 6 hours |
| `quiz_responses` (unpaid) | 7 days | `created_at` + 7d AND `payment_id IS NULL` | Daily |
| `meal_plans` metadata | 90 days | `created_at` + 90d | Daily |
| `meal_plans` PDF (Blob) | 91 days | `created_at` + 91d (90d + 24h grace) | Daily at 00:00 UTC |
| `payment_transactions` | 1 year | `created_at` + 1y | Monthly |
| `manual_resolution` | 1 year | `created_at` + 1y | Monthly |
| `magic_link_tokens` | 24 hours | `expires_at` | Daily |
| `email_blacklist` | 90 days | `expires_at` | Daily |
| `users` | Indefinite | User deletion request | N/A |

---

## Migration Strategy

**Alembic Migration Order**:
1. Create `users` table
2. Create `quiz_responses` table (FK to `users`)
3. Create `meal_plans` table
4. Create `payment_transactions` table (FK to `meal_plans`)
5. Create `manual_resolution` table
6. Create `magic_link_tokens` table
7. Create `email_blacklist` table

**Sample Alembic Migration** (auto-generated via `alembic revision --autogenerate`):
```python
# database/migrations/versions/001_initial_schema.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('normalized_email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_email', 'users', ['email'], unique=True)
    op.create_index('idx_user_normalized_email', 'users', ['normalized_email'])

    # QuizResponse table
    op.create_table(
        'quiz_responses',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('normalized_email', sa.String(length=255), nullable=False),
        sa.Column('quiz_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('calorie_target', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('payment_id', sa.String(length=255), nullable=True),
        sa.Column('pdf_delivered_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_quiz_normalized_email', 'quiz_responses', ['normalized_email'])
    op.create_index('idx_quiz_created_at', 'quiz_responses', ['created_at'])
    op.create_index('idx_quiz_pdf_delivered_at', 'quiz_responses', ['pdf_delivered_at'])

    # Additional tables follow same pattern...

def downgrade():
    op.drop_table('quiz_responses')
    op.drop_table('users')
    # Additional drops...
```

---

## Pydantic Schemas (API Layer)

```python
# backend/src/schemas/meal_plan.py
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

class PreferencesSummary(BaseModel):
    excluded_foods: List[str]
    preferred_proteins: List[str]
    dietary_restrictions: str

class QuizDataStep20(BaseModel):
    age: int = Field(ge=18, le=100)
    weight_kg: float = Field(gt=0)
    height_cm: float = Field(gt=0)
    goal: str  # weight_loss, muscle_gain, maintenance

class QuizSubmission(BaseModel):
    email: EmailStr
    step_1: str
    step_2: str
    step_3: List[str]
    # ... steps 4-19
    step_20: QuizDataStep20

class MealPlanResponse(BaseModel):
    id: str
    payment_id: str
    email: str
    pdf_blob_url: str
    calorie_target: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
```

---

## Next Steps

1. **Create Alembic migrations**: Generate initial schema migrations
2. **Implement SQLAlchemy models**: Complete all 6 entity models with relationships
3. **Create Pydantic schemas**: API request/response validation
4. **Write database utilities**: Connection pooling, session management
5. **Implement cleanup jobs**: Scheduled tasks for data retention policy
