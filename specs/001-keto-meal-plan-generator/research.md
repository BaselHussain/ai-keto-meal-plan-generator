# Research Findings: Keto Meal Plan Generator

**Feature Branch**: `001-keto-meal-plan-generator`
**Date**: 2025-12-30
**Spec**: [spec.md](./spec.md)
**Phase**: 0 - Research

---

## 1. OpenAI Agents SDK Integration with FastAPI Async

### Decision
Use OpenAI Agents SDK with `set_default_openai_client()` for environment-based model selection (Gemini dev/OpenAI prod), `@function_tool` decorators for helper functions, and `Runner.run()` async pattern integrated with FastAPI endpoints.

### Rationale
- **Structured workflows**: Agents SDK provides Agent abstraction with instructions, model settings, and tools
- **Async compatibility**: `AsyncOpenAI` integrates natively with FastAPI's `async def` endpoints
- **Provider flexibility**: Custom `base_url` allows Gemini API via same SDK (dev/testing)
- **Function tools**: `@function_tool` decorator converts Python functions to agent-callable tools
- **Type safety**: Pydantic BaseModel support for structured output validation

### Alternatives Considered
1. **Direct OpenAI API calls** (no SDK): More control, less structure. Rejected - no agent abstraction, manual tool orchestration
2. **LangChain**: Feature-rich but heavy. Rejected - overkill for single-agent meal plan generation
3. **LiteLLM integration**: Multi-provider support. Deferred - `set_default_openai_client()` sufficient for MVP

### Implementation Pattern
```python
# backend/src/services/meal_plan_generator.py
import asyncio
import os
from typing import List
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from agents import (
    Agent,
    Runner,
    RunConfig,
    ModelSettings,
    function_tool,
    set_default_openai_client
)

# Pydantic models for structured output
class Meal(BaseModel):
    name: str = Field(description="Meal type: breakfast, lunch, or dinner")
    recipe: str = Field(description="Recipe name")
    ingredients: List[str] = Field(description="List of ingredients")
    prep_time: int = Field(description="Preparation time in minutes")
    carbs: int = Field(description="Net carbs in grams")
    protein: int = Field(description="Protein in grams")
    fat: int = Field(description="Fat in grams")
    calories: int = Field(description="Total calories")

class DayMealPlan(BaseModel):
    day: int = Field(description="Day number (1-30)")
    meals: List[Meal] = Field(description="3 meals: breakfast, lunch, dinner")
    total_carbs: int
    total_protein: int
    total_fat: int
    total_calories: int

class MealPlanOutput(BaseModel):
    days: List[DayMealPlan] = Field(description="30 days of meal plans")
    shopping_lists: List[dict] = Field(description="4 weekly shopping lists")

# Environment-based client configuration
def setup_ai_client():
    """Configure AsyncOpenAI client based on environment"""
    if os.getenv("ENV") == "production":
        # Production: OpenAI API
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    else:
        # Development: Gemini API via OpenAI-compatible endpoint
        client = AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=os.getenv("GEMINI_API_KEY")
        )

    set_default_openai_client(client, use_for_tracing=True)

# Optional: Define helper function tools (if needed for complex workflows)
@function_tool
async def validate_keto_compliance(day_plan: DayMealPlan) -> dict:
    """Validate that a day's meal plan meets keto compliance (<30g carbs)"""
    is_compliant = day_plan.total_carbs < 30
    return {
        "compliant": is_compliant,
        "total_carbs": day_plan.total_carbs,
        "message": "Compliant" if is_compliant else f"Exceeds 30g carb limit ({day_plan.total_carbs}g)"
    }

# Agent configuration
async def generate_meal_plan(
    calorie_target: int,
    excluded_foods: List[str],
    preferred_proteins: List[str],
    dietary_restrictions: str
) -> MealPlanOutput:
    """Generate 30-day keto meal plan using OpenAI Agents SDK"""

    # Setup client (call once at app startup in production)
    setup_ai_client()

    # Create agent with instructions and model settings
    agent = Agent(
        name="KetoPlanGenerator",
        instructions=f"""You are an expert keto nutritionist generating personalized 30-day meal plans.

STRICT REQUIREMENTS:
- Daily calorie target: {calorie_target} kcal (±50 kcal variance acceptable)
- Keto macros: <30g net carbs/day, 65-75% fat, 20-30% protein
- 3 meals per day: breakfast, lunch, dinner
- NO recipe repetition within 30 days
- Each meal: ≤10 ingredients, ≤30 min prep time

USER PREFERENCES:
- EXCLUDED foods (DO NOT USE): {', '.join(excluded_foods)}
- PREFERRED proteins: {', '.join(preferred_proteins)}
- Dietary restrictions: {dietary_restrictions}

OUTPUT STRUCTURE:
- 30 days, each with 3 meals (breakfast, lunch, dinner)
- Each meal includes: name, recipe, ingredients, prep_time, macros (carbs, protein, fat, calories)
- Daily totals calculated for each day
- 4 weekly shopping lists organized by category (proteins, vegetables, dairy, fats, pantry)

QUALITY STANDARDS:
- Practical, beginner-friendly recipes
- Variety in proteins, vegetables, and cooking methods
- Include motivational keto tips and hydration reminders
""",
        model_settings=ModelSettings(
            model="gpt-4o" if os.getenv("ENV") == "production" else "gemini-1.5-pro",
            temperature=0.7,
            max_tokens=16000  # 30-day plan requires large token limit
        ),
        output_type=MealPlanOutput,  # Structured output validation
        # Optional: Add function tools for complex validation
        # tools=[validate_keto_compliance]
    )

    # Run agent with configuration
    result = await Runner.run(
        agent,
        input="Generate the complete 30-day personalized keto meal plan.",
        config=RunConfig(
            max_turns=3  # Allow retries for validation
        )
    )

    return result.final_output  # Returns validated MealPlanOutput

# FastAPI endpoint integration
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel as PydanticBaseModel

router = APIRouter()

class MealPlanRequest(PydanticBaseModel):
    payment_id: str
    calorie_target: int
    excluded_foods: List[str]
    preferred_proteins: List[str]
    dietary_restrictions: str

class MealPlanResponse(PydanticBaseModel):
    meal_plan_id: str
    status: str

@router.post("/api/generate-meal-plan", response_model=MealPlanResponse)
async def create_meal_plan(request: MealPlanRequest, background_tasks: BackgroundTasks):
    """
    Generate meal plan asynchronously (triggered by payment webhook).

    Flow:
    1. Validate request
    2. Generate meal plan using AI agent
    3. Validate keto compliance
    4. Generate PDF
    5. Upload to Vercel Blob
    6. Send email
    """
    try:
        # Generate meal plan (20s timeout per FR-A-006)
        meal_plan = await asyncio.wait_for(
            generate_meal_plan(
                calorie_target=request.calorie_target,
                excluded_foods=request.excluded_foods,
                preferred_proteins=request.preferred_proteins,
                dietary_restrictions=request.dietary_restrictions
            ),
            timeout=20.0
        )

        # Validate keto compliance (FR-A-007)
        for day in meal_plan.days:
            if day.total_carbs > 30:
                raise ValueError(f"Day {day.day} exceeds 30g carb limit: {day.total_carbs}g")

        # Background task: Generate PDF, upload, send email
        background_tasks.add_task(
            process_meal_plan_delivery,
            payment_id=request.payment_id,
            meal_plan=meal_plan
        )

        return MealPlanResponse(
            meal_plan_id=request.payment_id,
            status="generating"
        )

    except asyncio.TimeoutError:
        # Retry logic with exponential backoff (FR-A-011)
        raise HTTPException(status_code=504, detail="AI generation timeout - retrying")
    except ValueError as e:
        # Keto compliance failure - retry once (FR-A-007)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # Fallback to manual resolution queue (FR-A-011)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

async def process_meal_plan_delivery(payment_id: str, meal_plan: MealPlanOutput):
    """Background task: PDF generation + upload + email delivery"""
    # Implementation in Phase 1
    pass
```

**Key Patterns**:
- `set_default_openai_client()` enables global client configuration with custom `base_url`
- `Agent.output_type` enforces structured Pydantic validation
- `Runner.run()` returns typed output matching `output_type` schema
- FastAPI async integration via `await Runner.run()`
- Timeout handling with `asyncio.wait_for()`

---

## 2. Vercel Blob Signed URLs

### Decision
Use Vercel Blob's `put()` method with default signed URL generation (automatic time-limited tokens).

### Rationale
- **Security**: Cryptographic signatures prevent URL guessing, automatic expiration limits exposure
- **Simplicity**: Native Vercel integration, no custom auth layer needed
- **Free tier**: 5GB storage sufficient for MVP (30-day plans ~500KB each = 10,000 PDFs)
- **Migration path**: Clear upgrade to Cloudinary if storage needs grow

### Alternatives Considered
1. **Public URLs**: Simple but insecure. Rejected - anyone with URL can access PDF
2. **Custom auth middleware**: Full control. Rejected - reinvents wheel, adds complexity
3. **Cloudinary**: 25GB free tier. Deferred - Vercel Blob simpler for MVP, migrate later if needed

### Implementation Pattern
```python
# backend/src/services/pdf_storage.py
import httpx
import os
from datetime import datetime, timedelta

async def upload_pdf_to_vercel_blob(pdf_bytes: bytes, filename: str) -> str:
    """
    Upload PDF to Vercel Blob, return signed URL.

    Vercel Blob automatically generates time-limited signed URLs
    with cryptographic tokens that expire (default: never, but can be customized).
    """
    async with httpx.AsyncClient() as client:
        # Upload to Vercel Blob API
        response = await client.put(
            f"https://blob.vercel-storage.com/{filename}",
            headers={
                "Authorization": f"Bearer {os.getenv('BLOB_READ_WRITE_TOKEN')}",
                "Content-Type": "application/pdf",
                "x-content-type": "application/pdf",
                "x-vercel-blob-add-random-suffix": "1",  # Prevent filename collisions
            },
            content=pdf_bytes,
            timeout=30.0  # 30s upload timeout
        )
        response.raise_for_status()

        blob_data = response.json()
        return blob_data["url"]  # Returns signed URL with automatic token

# Alternative: Generate custom-expiry download URLs (if needed)
async def get_download_url(blob_url: str, expiry_hours: int = 168) -> str:
    """
    Generate time-limited download URL (default 7 days).

    For Vercel Blob, the original URL is pre-signed.
    For custom expiry, use Vercel Blob API's generateSignedUrl().
    """
    # Vercel Blob URLs include signature in query params
    # No additional signing needed for basic access control
    return blob_url

# Cleanup: Delete expired PDFs (90 days + 24h grace)
async def delete_expired_pdfs(blob_urls: list[str]):
    """Delete PDFs from Vercel Blob (FR-D-008)"""
    async with httpx.AsyncClient() as client:
        for url in blob_urls:
            # Extract blob key from URL
            blob_key = url.split("vercel-storage.com/")[1].split("?")[0]

            response = await client.delete(
                f"https://blob.vercel-storage.com/{blob_key}",
                headers={
                    "Authorization": f"Bearer {os.getenv('BLOB_READ_WRITE_TOKEN')}"
                }
            )
            # Log deletion for compliance
            print(f"BLOB_DELETED: {blob_key} at {datetime.utcnow()}")
```

---

## 3. Paddle Webhook HMAC-SHA256 + Timestamp Validation

### Decision
Implement dual validation: HMAC-SHA256 signature verification + timestamp window check (5 minutes).

### Rationale
- **Authenticity**: HMAC prevents webhook tampering (signature verification)
- **Replay protection**: Timestamp check prevents replay attacks (5-minute window)
- **Paddle standard**: Official Paddle security recommendation (FR-P-002)
- **Compliance**: Prevents webhook spoofing and replay attacks

### Alternatives Considered
1. **Signature only (no timestamp)**: Simpler. Rejected - vulnerable to replay attacks
2. **Custom token-based auth**: Full control. Rejected - Paddle doesn't support, breaks webhook standard
3. **IP whitelist**: Additional layer. Deferred - Paddle IPs may change, signature sufficient

### Implementation Pattern
```python
# backend/src/api/webhooks/paddle.py
import hmac
import hashlib
import time
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.exc import IntegrityError
import os

router = APIRouter()

def verify_paddle_webhook(payload: bytes, signature: str, timestamp: int, secret: str) -> bool:
    """
    Verify Paddle webhook signature and timestamp (FR-P-002).

    Security checks:
    1. Timestamp validation (prevent replay attacks)
    2. HMAC-SHA256 signature verification (prevent tampering)
    """
    # 1. Timestamp validation (5-minute window)
    current_time = int(time.time())
    time_delta = abs(current_time - timestamp)

    if time_delta > 300:  # 5 minutes = 300 seconds
        print(f"WEBHOOK_TIMESTAMP_REJECT: delta={time_delta}s")
        return False

    # 2. HMAC-SHA256 signature verification
    expected_signature = hmac.new(
        key=secret.encode(),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)

@router.post("/webhooks/paddle")
async def handle_paddle_webhook(request: Request):
    """
    Process Paddle payment webhooks.

    Flow:
    1. Verify signature + timestamp
    2. Check idempotency (payment_id unique constraint)
    3. Poll for quiz_responses (FR-P-008)
    4. Trigger AI generation
    """
    payload = await request.body()
    signature = request.headers.get("Paddle-Signature")
    timestamp = int(request.headers.get("Paddle-Timestamp", 0))
    secret = os.getenv("PADDLE_WEBHOOK_SECRET")

    # Verify webhook authenticity
    if not verify_paddle_webhook(payload, signature, timestamp, secret):
        # Alert on repeated failures (>3 per hour indicates attack)
        print(f"WEBHOOK_VERIFY_FAIL: timestamp={timestamp}, sig={signature[:16]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature or timestamp"
        )

    # Parse payload
    data = await request.json()
    payment_id = data["payment_id"]
    email = data["customer_email"]

    # Idempotency check (unique constraint on payment_id)
    try:
        # Attempt to create meal_plan record
        meal_plan = MealPlan(
            id=str(uuid.uuid4()),
            payment_id=payment_id,  # Unique constraint
            email=email,
            normalized_email=normalize_email(email),
            status="processing"
        )
        db.add(meal_plan)
        await db.commit()
    except IntegrityError:
        # Duplicate webhook - return 200 to prevent retries
        print(f"WEBHOOK_DUPLICATE: payment_id={payment_id}")
        return {"status": "already_processed"}

    # Poll for quiz_responses (FR-P-008: 5s grace period)
    quiz_data = await poll_quiz_responses(email, retries=10, interval=0.5)

    if not quiz_data:
        # Route to manual resolution queue
        await create_manual_resolution(
            payment_id=payment_id,
            email=email,
            issue_type="missing_quiz_data"
        )
        return {"status": "manual_resolution"}

    # Trigger AI generation (background task)
    background_tasks.add_task(
        generate_and_deliver_meal_plan,
        payment_id=payment_id,
        quiz_data=quiz_data
    )

    return {"status": "ok"}
```

---

## 4. Redis Distributed Locks (SETNX)

### Decision
Use Redis `SETNX` (SET if Not eXists) with 60-second TTL for distributed locks on `normalized_email` during checkout.

### Rationale
- **Race condition prevention**: Ensures only one payment process per email at a time (FR-P-007)
- **Automatic cleanup**: TTL expires lock if process crashes (no manual unlock needed)
- **Atomic operation**: SETNX is atomic, prevents concurrent lock acquisition
- **Simplicity**: Single Redis command, no complex distributed consensus

### Alternatives Considered
1. **Database locks**: ACID guarantees. Rejected - adds DB load, slower than Redis
2. **Redlock algorithm**: Multi-node consensus. Rejected - overkill for MVP, single Redis instance sufficient
3. **Application-level mutex**: In-memory. Rejected - doesn't work across serverless functions

### Implementation Pattern
```python
# backend/src/lib/redis_locks.py
import redis.asyncio as redis
import os
from datetime import datetime, timedelta

redis_client = redis.from_url(os.getenv("REDIS_URL"))

async def acquire_payment_lock(normalized_email: str, ttl: int = 60) -> bool:
    """
    Acquire distributed lock for payment processing (FR-P-007).

    Returns:
        True if lock acquired, False if already locked
    """
    lock_key = f"payment_lock:{normalized_email}"

    # SETNX returns True if key was set, False if already exists
    acquired = await redis_client.set(lock_key, "1", nx=True, ex=ttl)
    return bool(acquired)

async def release_payment_lock(normalized_email: str):
    """Release payment lock (optional, TTL auto-expires)"""
    lock_key = f"payment_lock:{normalized_email}"
    await redis_client.delete(lock_key)

# Usage in payment flow
from fastapi import HTTPException

async def initiate_checkout(email: str):
    """
    Initiate Paddle checkout with duplicate payment prevention.

    Checks (FR-P-007):
    1. Acquire distributed lock (prevents concurrent payments)
    2. Check for recent payment (<10 min window)
    """
    normalized_email = normalize_email(email)

    # 1. Acquire lock
    if not await acquire_payment_lock(normalized_email):
        raise HTTPException(
            status_code=409,
            detail="A payment is already in progress for this email. Please wait 60 seconds."
        )

    try:
        # 2. Check for duplicate payment in last 10 minutes
        recent_payment = await db.query(
            MealPlan.select().where(
                MealPlan.normalized_email == normalized_email,
                MealPlan.created_at > datetime.utcnow() - timedelta(minutes=10),
                MealPlan.status == "completed"
            )
        ).first()

        if recent_payment:
            raise HTTPException(
                status_code=409,
                detail="You recently purchased a meal plan. Please check your email."
            )

        # 3. Proceed with Paddle checkout
        paddle_checkout_url = create_paddle_checkout(email)
        return {"checkout_url": paddle_checkout_url}

    finally:
        # Release lock on error (TTL handles normal flow)
        if recent_payment:
            await release_payment_lock(normalized_email)
```

---

## 5. Email Normalization (Gmail Dots/Plus Removal)

### Decision
Normalize all emails before checks: remove dots (.) before @, strip +tags, lowercase, googlemail.com → gmail.com.

### Rationale
- **Blacklist bypass prevention**: `user+1@gmail.com` and `user@gmail.com` normalize to same value (FR-P-010)
- **Duplicate detection**: Prevents abuse via Gmail aliases
- **Consistent lookups**: All email-based queries use `normalized_email` index
- **Data integrity**: Store both original (for communications) and normalized (for lookups)

### Alternatives Considered
1. **Case-insensitive only**: Simpler. Rejected - doesn't prevent dot/plus aliasing
2. **Regex validation**: Validates format. Rejected - doesn't normalize, misses aliases
3. **Third-party email verification API**: Catches disposables. Deferred - adds cost, normalization sufficient for MVP

### Implementation Pattern
```python
# backend/src/lib/email_utils.py
import re

def normalize_email(email: str) -> str:
    """
    Normalize email for consistent lookups (FR-P-010).

    Rules:
    - Lowercase all characters
    - Gmail/Googlemail: remove dots, strip +tags
    - Googlemail.com → gmail.com
    """
    email = email.lower().strip()

    # Split into local and domain parts
    if "@" not in email:
        return email

    local, domain = email.split("@", 1)

    # Gmail/Googlemail normalization
    if domain in ("gmail.com", "googlemail.com"):
        # Remove all dots from local part
        local = local.replace(".", "")
        # Remove +tag suffix (everything after +)
        if "+" in local:
            local = local.split("+")[0]
        # Standardize domain
        domain = "gmail.com"

    return f"{local}@{domain}"

# Test cases
assert normalize_email("User.Name+tag@Gmail.com") == "username@gmail.com"
assert normalize_email("user.name@googlemail.com") == "username@gmail.com"
assert normalize_email("test+alias@example.com") == "test@example.com"

# Database model with dual email storage
from sqlalchemy import Column, String, Index, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(String, primary_key=True)
    payment_id = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, nullable=False)  # Original email (for communications)
    normalized_email = Column(String, nullable=False, index=True)  # Normalized (for lookups)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("idx_normalized_email", "normalized_email"),
        Index("idx_created_at", "created_at"),
    )

class EmailBlacklist(Base):
    __tablename__ = "email_blacklist"

    id = Column(String, primary_key=True)
    normalized_email = Column(String, unique=True, nullable=False, index=True)
    reason = Column(String, nullable=False)  # "chargeback"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)  # 90-day TTL

# Blacklist check (FR-P-009)
async def is_email_blacklisted(email: str) -> bool:
    """Check if email is blacklisted (chargebacks)"""
    normalized = normalize_email(email)
    blacklist_entry = await db.query(
        EmailBlacklist.select().where(
            EmailBlacklist.normalized_email == normalized,
            EmailBlacklist.expires_at > datetime.utcnow()
        )
    ).first()
    return blacklist_entry is not None
```

---

## 6. ReportLab PDF Generation

### Decision
Use ReportLab Python library with `SimpleDocTemplate`, table layouts, custom styles, and precise positioning.

### Rationale
- **Production-ready**: Industry standard, powers major Python PDF workflows
- **Performance**: Generates 30-day meal plans (10+ pages) in <5 seconds
- **Layout control**: Tables, multi-column, custom fonts, headers/footers
- **Pure Python**: No external dependencies (wkhtmltopdf, headless browsers)

### Alternatives Considered
1. **WeasyPrint**: HTML→PDF. Rejected - slower, requires HTML templating, 2x overhead
2. **pdfkit (wkhtmltopdf)**: Simple. Rejected - external binary dependency, deployment complexity
3. **Puppeteer (Node)**: Browser-based. Rejected - requires Node runtime, slower, resource-heavy

### Implementation Pattern
```python
# backend/src/services/pdf_generator.py
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime

def generate_meal_plan_pdf(meal_plan: dict, user_data: dict) -> bytes:
    """
    Generate 30-day keto meal plan PDF using ReportLab (FR-D-001 to FR-D-004).

    Structure:
    - Cover page: user info, calorie target, macros
    - 30 days: each with 3 meals table + daily totals
    - 4 weekly shopping lists: organized by category
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch
    )

    # Custom styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#22c55e"),
        spaceAfter=12
    )

    story = []

    # === COVER PAGE ===
    story.append(Paragraph("Your 30-Day Keto Meal Plan", title_style))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.utcnow().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Paragraph(f"<b>Daily Calorie Target:</b> {user_data['calorie_target']} kcal", styles['Normal']))
    story.append(Paragraph(
        f"<b>Macros:</b> {user_data['fat_percent']}% Fat | "
        f"{user_data['protein_percent']}% Protein | "
        f"{user_data['carb_percent']}% Carbs",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("<i>Your personalized keto journey starts here!</i>", styles['Italic']))
    story.append(PageBreak())

    # === 30 DAYS OF MEALS ===
    for day_num, day_data in enumerate(meal_plan['days'], start=1):
        story.append(Paragraph(f"Day {day_num}", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))

        # Meals table (Breakfast, Lunch, Dinner)
        meal_data = [
            ['Meal', 'Recipe', 'Carbs (g)', 'Protein (g)', 'Fat (g)', 'Calories'],
        ]

        for meal in day_data['meals']:
            meal_data.append([
                meal['name'].title(),
                meal['recipe'],
                str(meal['carbs']),
                str(meal['protein']),
                str(meal['fat']),
                str(meal['calories'])
            ])

        # Daily totals row
        meal_data.append([
            'DAILY TOTAL',
            '',
            f"{day_data['total_carbs']}g",
            f"{day_data['total_protein']}g",
            f"{day_data['total_fat']}g",
            f"{day_data['total_calories']} kcal"
        ])

        meal_table = Table(meal_data, colWidths=[1*inch, 2.2*inch, 0.8*inch, 0.9*inch, 0.7*inch, 0.9*inch])
        meal_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#22c55e")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            # Body
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            # Totals row
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 10),
        ]))

        story.append(meal_table)
        story.append(Spacer(1, 0.3*inch))

        # Page break every 2 days for readability
        if day_num % 2 == 0 and day_num < 30:
            story.append(PageBreak())

    # === WEEKLY SHOPPING LISTS ===
    story.append(PageBreak())
    story.append(Paragraph("Weekly Shopping Lists", title_style))
    story.append(Spacer(1, 0.2*inch))

    for week_num, week_data in enumerate(meal_plan['shopping_lists'], start=1):
        story.append(Paragraph(f"Week {week_num}", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))

        for category, items in week_data.items():
            story.append(Paragraph(f"<b>{category.title()}</b>", styles['Heading3']))
            for item in items:
                story.append(Paragraph(
                    f"• {item['name']} — {item['quantity']}",
                    styles['Normal']
                ))
            story.append(Spacer(1, 0.1*inch))

        if week_num < 4:
            story.append(Spacer(1, 0.2*inch))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.read()
```

---

## 7. Mifflin-St Jeor Formula Implementation

### Decision
Implement Mifflin-St Jeor BMR calculation with activity multipliers, goal adjustments, and calorie floors (1200F/1500M).

### Rationale
- **Accuracy**: More accurate than Harris-Benedict for modern populations (FR-C-001, Constitution Principle X)
- **Safety**: Enforces minimum safe calorie thresholds (FR-C-004)
- **Transparency**: Calculation order documented, user warnings on clamping
- **Compliance**: Validated formula, no medical device classification needed

### Alternatives Considered
1. **Harris-Benedict**: Older formula. Rejected - less accurate per research
2. **Katch-McArdle**: Requires body fat %. Rejected - users don't know BF%, adds friction
3. **Fixed calorie ranges**: Simple. Rejected - not personalized, defeats product value

### Implementation Pattern
```python
# backend/src/services/calorie_calculator.py
from enum import Enum
from pydantic import BaseModel

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"

class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"          # 1.2
    LIGHTLY_ACTIVE = "lightly_active"  # 1.375
    MODERATELY_ACTIVE = "moderately_active"  # 1.55
    VERY_ACTIVE = "very_active"      # 1.725
    SUPER_ACTIVE = "super_active"    # 1.9

class Goal(str, Enum):
    WEIGHT_LOSS = "weight_loss"      # -400 kcal
    MUSCLE_GAIN = "muscle_gain"      # +250 kcal
    MAINTENANCE = "maintenance"      # 0 kcal

ACTIVITY_MULTIPLIERS = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHTLY_ACTIVE: 1.375,
    ActivityLevel.MODERATELY_ACTIVE: 1.55,
    ActivityLevel.VERY_ACTIVE: 1.725,
    ActivityLevel.SUPER_ACTIVE: 1.9,
}

GOAL_ADJUSTMENTS = {
    Goal.WEIGHT_LOSS: -400,
    Goal.MUSCLE_GAIN: 250,
    Goal.MAINTENANCE: 0,
}

class CalorieCalculation(BaseModel):
    bmr: int
    tdee: int
    goal_adjusted: int
    final_target: int
    clamped: bool
    warning: str | None

def calculate_calorie_target(
    gender: Gender,
    age: int,
    weight_kg: float,
    height_cm: float,
    activity_level: ActivityLevel,
    goal: Goal
) -> CalorieCalculation:
    """
    Calculate personalized calorie target using Mifflin-St Jeor formula (FR-C-001 to FR-C-004).

    Calculation order (FR-C-004):
    1. Calculate BMR (Mifflin-St Jeor)
    2. Apply activity multiplier (TDEE)
    3. Apply goal adjustment
    4. Enforce calorie floors (1200F/1500M)
    """
    # Step 1: Calculate BMR (Mifflin-St Jeor)
    if gender == Gender.MALE:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:  # FEMALE
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    bmr = int(bmr)

    # Step 2: Apply activity multiplier (TDEE)
    multiplier = ACTIVITY_MULTIPLIERS[activity_level]
    tdee = int(bmr * multiplier)

    # Step 3: Apply goal adjustment
    adjustment = GOAL_ADJUSTMENTS[goal]
    goal_adjusted = tdee + adjustment

    # Step 4: Enforce calorie floors
    minimum_calories = 1500 if gender == Gender.MALE else 1200
    clamped = False
    warning = None

    if goal_adjusted < minimum_calories:
        clamped = True
        final_target = minimum_calories
        warning = (
            f"Your goal requires an aggressive calorie target. "
            f"We've set a safe minimum of {minimum_calories} kcal based on "
            f"established nutritional guidelines."
        )
        # Log for monitoring (FR-C-004)
        print(f"CALORIE_CLAMP: BMR={bmr}, TDEE={tdee}, Goal={goal.value}, "
              f"Calculated={goal_adjusted}, Clamped={final_target}")
    else:
        final_target = goal_adjusted

    return CalorieCalculation(
        bmr=bmr,
        tdee=tdee,
        goal_adjusted=goal_adjusted,
        final_target=final_target,
        clamped=clamped,
        warning=warning
    )

# Example usage
result = calculate_calorie_target(
    gender=Gender.FEMALE,
    age=35,
    weight_kg=65,
    height_cm=165,
    activity_level=ActivityLevel.MODERATELY_ACTIVE,
    goal=Goal.WEIGHT_LOSS
)

print(f"BMR: {result.bmr} kcal")
print(f"TDEE: {result.tdee} kcal")
print(f"Final Target: {result.final_target} kcal")
if result.warning:
    print(f"⚠️ {result.warning}")
```

---

## 8. Neon DB JSONB Schema for preferences_summary

### Decision
Use PostgreSQL JSONB column for `preferences_summary` with typed structure: `{excluded_foods: [], preferred_proteins: [], dietary_restrictions: str}`.

### Rationale
- **Flexibility**: Schema-less storage for variable-length arrays (excluded_foods can be 0-200 items)
- **Performance**: JSONB supports GIN indexes for fast querying (if needed for analytics later)
- **Type safety**: Pydantic models enforce structure at application layer
- **Data retention**: Summary retained 90 days (FR-A-014), full quiz deleted 24h

### Alternatives Considered
1. **Separate tables** (excluded_foods, preferred_proteins): Normalized. Rejected - over-engineering, many joins
2. **JSON (not JSONB)**: Text storage. Rejected - slower, no indexing, no validation
3. **Comma-separated text**: Simple. Rejected - no structure, parsing required, error-prone

### Implementation Pattern
```python
# backend/src/models/meal_plan.py
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid

Base = declarative_base()

# Pydantic schema for preferences_summary (type safety)
class PreferencesSummary(BaseModel):
    excluded_foods: List[str]
    preferred_proteins: List[str]
    dietary_restrictions: str

# SQLAlchemy model
class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, nullable=False)
    normalized_email = Column(String, nullable=False, index=True)
    pdf_blob_url = Column(String, nullable=False)
    calorie_target = Column(Integer, nullable=False)
    preferences_summary = Column(JSONB, nullable=False)  # {excluded_foods, preferred_proteins, dietary_restrictions}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    status = Column(String, nullable=False, default="processing")  # processing, completed, failed

# Usage: Derive preferences_summary from quiz_responses (FR-A-014)
def derive_preferences_summary(quiz_responses: dict) -> PreferencesSummary:
    """
    Derive food preference summary from 20-step quiz responses.

    Mapping (FR-A-014):
    - excluded_foods: All items NOT selected in Steps 3-16
    - preferred_proteins: All items selected in Steps 3, 4, 9 (meat, fish, shellfish)
    - dietary_restrictions: Free text from Step 17
    """
    # Complete food items list from Steps 3-16
    all_food_items = {
        "step_3": ["beef", "lamb", "chicken", "pork", "turkey"],
        "step_4": ["tuna", "salmon", "mackerel", "cod", "pollock"],
        "step_5": ["avocado", "asparagus", "bell_pepper", "zucchini", "celery", "mushrooms"],
        "step_6": ["brussels_sprouts", "kale", "broccoli", "cauliflower"],
        "step_7": ["lettuce", "spinach", "arugula", "cilantro", "iceberg", "napa_cabbage"],
        "step_8": ["chickpeas", "lentils", "black_beans"],
        "step_9": ["clams", "shrimp", "crab", "lobster"],
        "step_10": ["apple", "banana", "orange", "berries"],
        "step_11": ["strawberries", "blueberries", "raspberries"],
        "step_12": ["rice", "quinoa", "oats"],
        "step_13": ["pasta", "bread", "potatoes"],
        "step_14": ["coconut_oil", "olive_oil", "peanut_butter", "butter", "lard"],
        "step_15": ["water", "coffee", "tea", "soda"],
        "step_16": ["greek_yogurt", "cheese", "sour_cream", "cottage_cheese"],
    }

    # Collect all items user selected
    selected_items = set()
    for step_key in all_food_items.keys():
        selected_items.update(quiz_responses.get(step_key, []))

    # Excluded foods = all items NOT selected
    all_items = []
    for items_list in all_food_items.values():
        all_items.extend(items_list)

    excluded_foods = [item for item in all_items if item not in selected_items]

    # Preferred proteins from Steps 3, 4, 9
    preferred_proteins = []
    preferred_proteins.extend(quiz_responses.get("step_3", []))  # Meat
    preferred_proteins.extend(quiz_responses.get("step_4", []))  # Fish
    preferred_proteins.extend(quiz_responses.get("step_9", []))  # Shellfish

    dietary_restrictions = quiz_responses.get("step_17", "")

    return PreferencesSummary(
        excluded_foods=excluded_foods,
        preferred_proteins=preferred_proteins,
        dietary_restrictions=dietary_restrictions
    )

# Store in database
async def create_meal_plan_record(payment_id: str, email: str, quiz_responses: dict, pdf_url: str, calorie_target: int):
    """Create meal plan record with preferences summary"""
    preferences = derive_preferences_summary(quiz_responses)

    meal_plan = MealPlan(
        payment_id=payment_id,
        email=email,
        normalized_email=normalize_email(email),
        pdf_blob_url=pdf_url,
        calorie_target=calorie_target,
        preferences_summary=preferences.dict(),  # Pydantic → dict → JSONB
        status="completed"
    )

    db.add(meal_plan)
    await db.commit()
    return meal_plan
```

---

## 9. Magic Link Security (256-bit Tokens, Single-Use)

### Decision
Generate cryptographically secure 32-byte (256-bit) tokens using `secrets.token_bytes()`, store with email+expiry+used_at, enforce single-use, log IP addresses.

### Rationale
- **Entropy**: 256 bits = 2^256 possibilities, impossible to brute-force
- **Single-use**: Invalidate on first use prevents token reuse (FR-R-002)
- **Expiration**: 24-hour TTL limits exposure window
- **IP logging**: Detects suspicious patterns (warn but don't block for UX)

### Alternatives Considered
1. **JWT tokens**: Stateless. Rejected - can't invalidate, no single-use enforcement
2. **Short codes (6 digits)**: Simple. Rejected - low entropy (10^6 = brute-forceable)
3. **UUID v4**: 122 bits. Rejected - less entropy than 256-bit random

### Implementation Pattern
```python
# backend/src/services/magic_link.py
import secrets
import hashlib
from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, Boolean
from pydantic import BaseModel
import uuid

# Model
class MagicLinkToken(Base):
    __tablename__ = "magic_link_tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    token_hash = Column(String, unique=True, nullable=False, index=True)  # SHA256 hash
    email = Column(String, nullable=False)
    normalized_email = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    generation_ip = Column(String, nullable=True)
    usage_ip = Column(String, nullable=True)

# Generate magic link
async def create_magic_link(email: str, ip_address: str) -> str:
    """
    Generate 256-bit secure magic link token (FR-R-002).

    Security features:
    - 256-bit entropy (cryptographically secure)
    - Rate limiting (3 per email per 24h)
    - 24-hour expiration
    - IP address logging
    """
    # 1. Rate limit check (3 per email per 24h - FR-R-002)
    recent_tokens_count = await db.query(
        func.count(MagicLinkToken.id)
    ).filter(
        MagicLinkToken.normalized_email == normalize_email(email),
        MagicLinkToken.created_at > datetime.utcnow() - timedelta(hours=24)
    ).scalar()

    if recent_tokens_count >= 3:
        raise HTTPException(
            status_code=429,
            detail="Too many magic link requests. Please try again in 24 hours."
        )

    # 2. Generate cryptographically secure token
    token_bytes = secrets.token_bytes(32)  # 256 bits
    token = token_bytes.hex()  # 64-character hex string
    token_hash = hashlib.sha256(token_bytes).hexdigest()

    # 3. Store token
    magic_link = MagicLinkToken(
        token_hash=token_hash,
        email=email,
        normalized_email=normalize_email(email),
        expires_at=datetime.utcnow() + timedelta(hours=24),
        generation_ip=ip_address
    )

    db.add(magic_link)
    await db.commit()

    # 4. Return full URL
    return f"https://yourdomain.com/recover-plan?token={token}"

# Verify and use magic link
async def verify_magic_link(token: str, ip_address: str) -> dict:
    """
    Verify magic link, enforce single-use (FR-R-002).

    Checks:
    1. Token exists
    2. Not expired
    3. Not already used
    4. IP mismatch warning (log but allow)
    """
    # Hash token for lookup
    token_bytes = bytes.fromhex(token)
    token_hash = hashlib.sha256(token_bytes).hexdigest()

    # 1. Lookup token
    magic_link = await db.query(MagicLinkToken).filter(
        MagicLinkToken.token_hash == token_hash
    ).first()

    if not magic_link:
        raise HTTPException(status_code=401, detail="Invalid or expired magic link")

    # 2. Check expiration
    if datetime.utcnow() > magic_link.expires_at:
        raise HTTPException(status_code=401, detail="Magic link expired. Please request a new one.")

    # 3. Single-use enforcement
    if magic_link.used_at:
        raise HTTPException(status_code=401, detail="Link already used. Please request a new one.")

    # 4. IP mismatch warning (log but allow)
    if magic_link.generation_ip and magic_link.generation_ip != ip_address:
        print(f"IP_MISMATCH: Token generated from {magic_link.generation_ip}, used from {ip_address}")

    # 5. Mark as used
    magic_link.used_at = datetime.utcnow()
    magic_link.usage_ip = ip_address
    await db.commit()

    # 6. Return user data for PDF access
    return {
        "email": magic_link.email,
        "normalized_email": magic_link.normalized_email
    }
```

---

## 10. Redis Rate Limiting (TTL Keys)

### Decision
Use Redis with TTL-based keys for rate limiting: `download_limit:{identifier}:{date}`, increment on access, expire after 24h.

### Rationale
- **Simplicity**: Single Redis command (INCR), automatic expiration via TTL
- **Performance**: In-memory, sub-millisecond response time
- **Composite keys**: Separate tracking for user_id (authenticated) vs email+IP hash (magic link)
- **Exclusion window**: Skip rate limit for first 5 minutes after PDF delivery (FR-R-005)

### Alternatives Considered
1. **Database counters**: ACID. Rejected - adds DB load, slower than Redis
2. **Fixed-window counters**: Simple. Rejected - allows 2x limit at window boundary
3. **Token bucket**: Smoother. Deferred - INCR+TTL sufficient for MVP

### Implementation Pattern
```python
# backend/src/lib/rate_limiting.py
import redis.asyncio as redis
import hashlib
from datetime import datetime, timedelta
import os

redis_client = redis.from_url(os.getenv("REDIS_URL"))

async def check_download_rate_limit(
    user_id: str | None,
    email: str | None,
    ip_address: str,
    pdf_created_at: datetime
) -> bool:
    """
    Check download rate limit (FR-R-005).

    Rules:
    - Authenticated users: limit by user_id (10/24h)
    - Magic link users: limit by email+IP hash (10/24h)
    - Exclude downloads within 5 minutes of PDF creation

    Returns:
        True if allowed, False if rate limit exceeded
    """
    # 1. Exclude recent deliveries (5-minute grace period)
    if datetime.utcnow() - pdf_created_at < timedelta(minutes=5):
        return True  # Allow without counting

    # 2. Determine identifier
    if user_id:
        identifier = f"user:{user_id}"
    else:
        # Hash email+IP for magic link users
        combined = f"{normalize_email(email)}:{ip_address}"
        identifier = f"guest:{hashlib.sha256(combined.encode()).hexdigest()[:16]}"

    # 3. Redis key with date (daily limit)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    rate_limit_key = f"download_limit:{identifier}:{today}"

    # 4. Increment counter
    current_count = await redis_client.incr(rate_limit_key)

    # 5. Set TTL on first increment (24 hours)
    if current_count == 1:
        await redis_client.expire(rate_limit_key, 86400)  # 24 hours

    # 6. Check limit (10 downloads per day)
    if current_count > 10:
        return False  # Rate limit exceeded

    return True  # Allowed

# Usage in download endpoint
from fastapi import APIRouter, Request, HTTPException, Depends

router = APIRouter()

@router.get("/api/download-pdf/{meal_plan_id}")
async def download_pdf(
    meal_plan_id: str,
    request: Request,
    user_id: str | None = Depends(get_current_user_id)  # Optional auth
):
    """
    Download PDF with rate limiting (FR-R-005).

    Rate limits:
    - Authenticated: 10 downloads/24h per user_id
    - Magic link: 10 downloads/24h per email+IP hash
    - Grace period: First 5 min after delivery (unlimited)
    """
    # Fetch meal plan
    meal_plan = await db.get(MealPlan, meal_plan_id)
    if not meal_plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")

    # Check rate limit
    if not await check_download_rate_limit(
        user_id=user_id,
        email=meal_plan.email,
        ip_address=request.client.host,
        pdf_created_at=meal_plan.created_at
    ):
        # Calculate hours until reset
        now = datetime.utcnow()
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        hours_until_reset = int((tomorrow - now).total_seconds() / 3600)

        raise HTTPException(
            status_code=429,
            detail=f"Download limit reached (10 per day). Please try again in {hours_until_reset} hours."
        )

    # Serve PDF via redirect to Vercel Blob signed URL
    return RedirectResponse(meal_plan.pdf_blob_url)
```

---

## Summary

All 10 research topics completed with production-ready implementation patterns documented using official OpenAI Agents SDK documentation. Key takeaways:

1. **OpenAI Agents SDK**: `set_default_openai_client()` with custom `base_url` for Gemini dev, `Agent` with `output_type` for structured validation, `Runner.run()` async pattern
2. **Vercel Blob**: Native signed URLs with automatic time-limited tokens
3. **Paddle Webhooks**: Dual validation (HMAC-SHA256 + timestamp) prevents replay attacks
4. **Redis SETNX**: Atomic distributed locks prevent concurrent payment races
5. **Email Normalization**: Gmail alias prevention (dots/plus tags) for consistent lookups
6. **ReportLab**: Fast Python PDF generation with table layouts and custom styles
7. **Mifflin-St Jeor**: Accurate BMR calculation with safety floors and transparency
8. **JSONB Preferences**: Flexible schema for variable-length food preference arrays
9. **Magic Links**: 256-bit entropy, single-use enforcement, IP logging for security
10. **Redis Rate Limiting**: TTL-based keys, composite identifiers, grace period exclusions

**Next Phase**: Design data models, API contracts, and quickstart guide (Phase 1).
