# Implementation Tasks: AI-Powered Keto Meal Plan Generator

**Feature Branch**: `001-keto-meal-plan-generator`
**Date**: 2025-12-30
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Data Model**: [data-model.md](./data-model.md)

---

## Task Format

```
- [ ] [TaskID] [P] [StoryN] Description with file path
```

**Legend**:
- `TaskID`: Sequential task identifier (T001, T002, etc.)
- `[P]`: Parallelizable (can run independently)
- `[Story]`: User Story reference (US1-US5, only for user-facing features)
- Description: Clear action with specific file path

**Task Duration**: Each task 15-30 minutes

---

## Testing Strategy

**Comprehensive testing is integrated into critical phases** to ensure quality, security, and performance:

### Testing Phases
- **Phase 2.5**: Unit & integration tests for data layer (email normalization, calorie calc, database models)
- **Phase 6.9**: Integration & E2E tests for payment/AI pipeline (webhooks, AI generation, PDF, email delivery)
- **Phase 7.6**: Integration tests for recovery & accounts (magic links, rate limiting, account creation)
- **Phase 9.5**: Integration tests for security & automation (chargeback, refund abuse, SLA monitoring)
- **Phase 10.4**: E2E, load, security, and production verification tests

### Coverage Requirements
- **Unit Tests**: 80%+ coverage on `src/lib/` and `src/services/`
- **Integration Tests**: All critical flows (payment, AI, email, recovery)
- **E2E Tests**: Complete user journeys (quiz → payment → PDF → recovery)
- **Manual Tests**: AI quality (9/10 keto compliance), edge cases, success criteria

### Testing Commands
```bash
# Backend unit tests
pytest backend/tests/unit/ -v --cov=src/lib --cov=src/services

# Backend integration tests
pytest backend/tests/integration/ -v

# Backend E2E tests
pytest backend/tests/e2e/ -v

# Load testing
python scripts/load_test.py

# Security testing
pytest backend/tests/security/ -v
```

**Total Testing Tasks**: 31 (17.6% of total tasks, ensuring production-ready quality)

---

## Implementation Notes & Accepted Risks

### Accepted MVP Risks (Documented in Spec v1.3.0)

**1. Concurrent Payment Race Condition** (Session 2026-01-01)
- **Risk**: Theoretical race condition if Redis lock expires (60s TTL) between two devices before 10-minute duplicate payment check
- **Decision**: Accept as acceptable MVP risk
- **Rationale**: Narrow exploit window (must time precisely within 60s), two-layer protection (Redis lock + 10-min DB check), extremely rare in practice, additional complexity adds minimal value
- **Monitoring**: Track via payment analytics, address post-MVP if becomes real issue
- **Implementation**: T059 (Redis lock), T060 (10-min duplicate check)

**2. Email Normalization Scope** (Session 2026-01-01)
- **Scope**: Gmail-only normalization (remove dots, strip +tags, lowercase)
- **Decision**: Do not extend to Yahoo+, Outlook+, Protonmail aliases
- **Rationale**: Gmail is dominant provider (~30% market share), plus-tag aliasing primarily Gmail feature, other providers have proprietary alias systems harder to normalize reliably, diminishing returns vs complexity
- **Accepted Risk**: Potential bypass via non-Gmail providers acceptable for MVP
- **Implementation**: T025 (email normalization utility)

### Key Implementation Patterns

**On-Demand Signed URL Generation** (Session 2026-01-01)
- **Pattern**: Store permanent blob path in database, generate fresh signed URLs (1-hour expiry) on each download request
- **Prevents**: URL expiry mismatch during 90-day retention period (Vercel Blob signed URLs have limited default expiry)
- **Maintains**: Security (time-limited access), User Experience (PDF always accessible during retention)
- **Implementation**: T078 (blob service), T080 (store blob path), T107 (download endpoint), T082 (email link)

**Email Verification Validity** (Session 2026-01-01)
- **Pattern**: 6-digit code expires in 10 minutes, verified status valid for 24 hours
- **Allows**: Paddle modal abandonment and return without re-verification
- **Reduces**: Friction for legitimate users who got interrupted
- **Implementation**: T053 (verification service), T054 (API endpoints)

---

## Phase 1: Project Setup & Infrastructure (Foundation)

### 1.1 Repository Structure

- [x] [T001] [P] Create Next.js 14.x frontend app with TypeScript strict mode at `frontend/`
- [x] [T002] [P] Create FastAPI backend app with Python 3.11+ at `backend/src/main.py`
- [x] [T003] [P] Create database migrations directory at `database/migrations/` with Alembic config
- [x] [T004] [P] Create scripts directory for cleanup jobs at `scripts/`
- [x] [T005] [P] Add .env.example files for frontend and backend with all required environment variables

**Acceptance**: Directory structure matches plan.md, both apps initialize without errors

### 1.2 Dependencies Installation

- [x] [T006] [P] Install Next.js frontend dependencies: next, react, typescript, tailwind, framer-motion, react-hook-form, zod, @paddle/paddle-js, react-icons in `frontend/package.json`
- [x] [T007] [P] Install FastAPI backend dependencies: fastapi, uvicorn, sqlalchemy, alembic, pydantic, openai-agents>=0.1.0<1.0, reportlab, httpx, redis in `backend/requirements.txt`
- [x] [T008] [P] Configure TypeScript strict mode in `frontend/tsconfig.json` with path aliases
- [x] [T009] [P] Configure Tailwind CSS with custom green theme (#22c55e) in `frontend/tailwind.config.js`

**Acceptance**: `npm install` and `pip install -r requirements.txt` succeed, no dependency conflicts

### 1.3 Database & External Services

- [x] [T010] Create Neon DB connection utility at `backend/src/lib/database.py` with async SQLAlchemy session management
- [x] [T011] Create Redis connection utility at `backend/src/lib/redis_client.py` with connection pooling
- [x] [T012] [P] Setup Sentry error tracking integration in `backend/src/main.py` and `frontend/src/lib/sentry.ts`
- [x] [T013] [P] Create environment variable validation utilities at `backend/src/lib/env.py` and `frontend/src/lib/env.ts`

**Acceptance**: Database connection established, Redis ping succeeds, Sentry test errors logged

---

## Phase 2: Foundational Data Layer (Blocking Prerequisites)

### 2.1 Database Models (SQLAlchemy)

- [x] [T014] Create User model at `backend/src/models/user.py` with email normalization, password hash, timestamps (data-model.md lines 129-152)
- [x] [T015] Create QuizResponse model at `backend/src/models/quiz_response.py` with JSONB quiz_data, calorie_target, retention fields (data-model.md lines 212-234)
- [x] [T016] Create MealPlan model at `backend/src/models/meal_plan.py` with JSONB preferences_summary, payment_id unique constraint, refund_count (data-model.md lines 273-294)
- [x] [T016A] Create PaymentTransaction model at `backend/src/models/payment_transaction.py` with payment_id unique constraint, meal_plan_id FK, amount/currency/payment_method fields, payment_status enum (data-model.md lines 451-516)
- [x] [T017] Create ManualResolution model at `backend/src/models/manual_resolution.py` with SLA tracking, issue_type enum (data-model.md lines 324-346)
- [x] [T018] Create MagicLinkToken model at `backend/src/models/magic_link.py` with token_hash, single-use enforcement, IP logging (data-model.md lines 373-390)
- [x] [T019] Create EmailBlacklist model at `backend/src/models/email_blacklist.py` with normalized_email unique constraint, 90-day TTL (data-model.md lines 413-426)

**Acceptance**: All models import without errors, relationships defined, indexes created

### 2.2 Database Migrations

- [x] [T020] Generate initial Alembic migration for all 7 tables at `database/migrations/versions/001_initial_schema.py` (users, quiz_responses, meal_plans, payment_transactions, manual_resolution, magic_link_tokens, email_blacklist)
- [x] [T021] Run migration against Neon DB dev environment and verify schema creation
- [x] [T022] Create migration rollback test to ensure down() functions work correctly

**Acceptance**: Database schema matches data-model.md, all indexes and constraints present

### 2.3 Core Utilities

- [x] [T023] Create email normalization utility at `backend/src/lib/email_utils.py` with Gmail dot/plus removal logic (research.md lines 554-587)
- [x] [T024] Create Mifflin-St Jeor calorie calculator at `backend/src/services/calorie_calculator.py` with gender-specific formulas, activity multipliers, calorie floors (research.md lines 809-927)
- [x] [T025] Create food preference summary derivation logic at `backend/src/lib/preferences.py` to extract excluded_foods, preferred_proteins from quiz data (research.md lines 981-1032)
- [x] [T026] [P] Create Pydantic schemas for API validation at `backend/src/schemas/` (quiz, meal_plan, auth, recovery)

**Acceptance**: Unit tests pass for normalization (10 test cases), calorie calculation (6 scenarios), preference derivation (3 quiz variations)

### 2.4 Base API Router Setup

- [x] [T027] Create FastAPI app initialization at `backend/src/main.py` with CORS, middleware, Sentry
- [x] [T028] Create API router structure at `backend/src/api/` with health check endpoint
- [x] [T029] [P] Create error handling middleware at `backend/src/middleware/error_handler.py` with structured error responses

**Acceptance**: `GET /health` returns 200, error responses follow consistent JSON format

### 2.5 Unit & Integration Testing (Data Layer)

- [x] [T029A] Write unit tests for email normalization at `backend/tests/unit/test_email_utils.py`: Gmail dots removal, plus tags, case sensitivity, googlemail→gmail conversion (10 test cases)
- [x] [T029B] Write unit tests for Mifflin-St Jeor calculator at `backend/tests/unit/test_calorie_calculator.py`: male/female formulas, all 5 activity levels, 3 goals, calorie floor enforcement (12 test cases)
- [x] [T029C] Write unit tests for preference derivation at `backend/tests/unit/test_preferences.py`: excluded_foods extraction, preferred_proteins mapping, dietary_restrictions handling (6 test cases covering 3 quiz variations)
- [x] [T029D] Write integration tests for database models at `backend/tests/integration/test_models.py`: CRUD operations, unique constraints (payment_id, normalized_email), foreign keys, JSONB queries on quiz_data and preferences_summary
- [x] [T029E] Write migration tests at `backend/tests/integration/test_migrations.py`: alembic upgrade/downgrade, schema verification against data-model.md

**Acceptance**: pytest passes with 80%+ coverage on src/lib/ and src/services/, all 35+ test cases pass, no database constraint violations

---

## Phase 3: User Story 1 (P1) - Complete Quiz End-to-End

### 3.1 Quiz UI Components (Frontend)

- [X] [T030] [US1] Create QuizContainer component at `frontend/src/components/quiz/QuizContainer.tsx` with step routing, progress display
- [X] [T031] [US1] Create StepProgress component at `frontend/src/components/quiz/StepProgress.tsx` showing "Step X of 20"
- [X] [T032] [US1] Create GenderSelection component (Step 1) at `frontend/src/components/quiz/steps/Step01Gender.tsx` with radio buttons
- [X] [T033] [US1] Create ActivityLevelSelection component (Step 2) at `frontend/src/components/quiz/steps/Step02Activity.tsx` with 5 levels
- [X] [T034] [US1] Create FoodSelectionGrid component at `frontend/src/components/quiz/FoodSelectionGrid.tsx` with 64x64px colored SVG icons (React Icons), reusable for Steps 3-16
- [X] [T035] [US1] Create BiometricForm component (Step 20) at `frontend/src/components/quiz/steps/Step20Biometrics.tsx` with age, weight, height, goal inputs and privacy badge
- [X] [T036] [US1] Create DietaryRestrictionsInput component (Step 17) at `frontend/src/components/quiz/steps/Step17Restrictions.tsx` with 500-char textarea and privacy warning (FR-Q-004)

**Acceptance**: All components render, icons display in color, responsive on 360px mobile

### 3.2 Quiz State Management

- [X] [T037] [US1] Create quiz state hook at `frontend/src/hooks/useQuizState.ts` with React state + localStorage persistence
- [X] [T038] [US1] Implement quiz data validation schemas using Zod at `frontend/src/lib/validators/quiz.ts` for all 20 steps
- [X] [T039] [US1] Create quiz submission handler at `frontend/src/services/quizService.ts` with API client calls

**Acceptance**: State persists on page reload, validation shows inline errors, submission triggers API call

### 3.3 Quiz Backend API

- [X] [T040] [US1] Create quiz submission endpoint `POST /api/quiz/submit` at `backend/src/api/quiz.py` that saves to quiz_responses table
- [X] [T041] [US1] Implement calorie calculation integration in quiz submission using calorie_calculator service
- [X] [T042] [US1] Add total food item validation (10-item minimum, blocking error; 10-14 warning) per FR-Q-017

**Acceptance**: Quiz submission saves to database, calorie_target calculated correctly, food validation works

### 3.4 Review Screen

- [X] [T043] [US1] Create ReviewScreen component at `frontend/src/components/quiz/ReviewScreen.tsx` displaying quiz summary, calorie breakdown, "Proceed to Payment" button
- [X] [T044] [US1] Implement calorie breakdown display showing BMR, activity multiplier, goal adjustment, final target
- [X] [T045] [US1] Add calorie floor warning display if user hit 1200/1500 minimum threshold

**Acceptance**: Review screen shows all user data, calorie math visible, payment button enabled only after quiz complete

---

## Phase 4: User Story 2 (P2) - Navigate Backward Through Quiz

### 4.1 Back Button Logic

- [X] [T046] [US2] Implement back navigation in QuizContainer at `frontend/src/components/quiz/QuizContainer.tsx` with state restoration
- [X] [T047] [US2] Add Back button UI component with disabled state on Step 1
- [X] [T048] [US2] Create state restoration tests to verify data persists when navigating backward

**Acceptance**: User clicks Back from Step 10, Step 9 data restored, no data loss, Back disabled on Step 1

---

## Phase 5: User Story 3 (P2) - Privacy Messaging & Data Reassurance

### 5.1 Privacy UI Components

- [X] [T049] [US3] Create PrivacyBadge component at `frontend/src/components/quiz/PrivacyBadge.tsx` with lock icon and "100% Private & Confidential" text
- [X] [T050] [US3] Add privacy notice to Step 17 (DietaryRestrictions) with warning text per FR-Q-004
- [X] [T051] [US3] Add privacy messaging to Step 20 (Biometrics) above input fields with tooltip explaining data deletion policy
- [X] [T052] [US3] [P] Create privacy policy page at `frontend/src/pages/privacy.tsx` with GDPR compliance text

**Acceptance**: Lock icon displays on Steps 17 and 20, tooltip works, privacy policy link opens in new tab - ✅ COMPLETED

---

## Phase 6: Payment & AI Generation (Critical Path)

### 6.1 Email Verification (Pre-Payment)

- [ ] [T053] Create email verification code generator at `backend/src/services/email_verification.py` with 6-digit codes, 10-min code expiry, 24-hour verified status validity, Redis storage for both code and verified status (FR-Q-019)
- [ ] [T054] Create email verification API endpoints at `backend/src/api/verification.py`: `POST /send-code`, `POST /verify-code` with verified status tracking (expires 24h after successful verification)
- [ ] [T055] [US1] Create EmailVerification component at `frontend/src/components/quiz/EmailVerification.tsx` with code input, resend button (60s cooldown), verified status persistence
- [ ] [T056] Integrate Resend email service for verification code delivery at `backend/src/services/email_service.py`

**Acceptance**: Verification code sent to email, user enters code, payment button enables only after verification success, verified status valid for 24h (allows Paddle modal abandonment and return), after 24h user must re-verify

### 6.2 Paddle Payment Integration

- [ ] [T057] Install Paddle.js SDK and create checkout integration at `frontend/src/lib/paddle.ts` with environment-based keys
- [ ] [T058] [US1] Create checkout modal trigger in ReviewScreen with verified email passed as readonly customer_email parameter (FR-P-003)
- [ ] [T059] Implement duplicate payment prevention: Redis distributed lock on normalized_email at `backend/src/lib/payment_locks.py` (research.md lines 460-529)
- [ ] [T060] Create payment duplicate check (10-min window) in `backend/src/services/payment_service.py` before initiating checkout
- [ ] [T061] Check email blacklist before checkout at `backend/src/api/checkout.py` using normalized_email lookup

**Acceptance**: Paddle modal opens, email readonly, duplicate payment blocked with user-friendly error, blacklisted emails rejected

### 6.3 Payment Webhook Handler

- [ ] [T062] Create Paddle webhook endpoint `POST /webhooks/paddle` at `backend/src/api/webhooks/paddle.py`
- [ ] [T063] Implement HMAC-SHA256 + timestamp validation in webhook handler (research.md lines 337-438)
- [ ] [T064] Implement idempotency check using payment_id unique constraint with IntegrityError handling
- [ ] [T064A] Create payment_transactions record on successful webhook validation at `backend/src/services/payment_service.py`: extract payment_id, amount, currency, payment_method, customer_email, paddle_created_at from webhook payload (FR-P-013)
- [ ] [T064B] Normalize customer_email per FR-P-010 before storing in payment_transactions (remove dots, strip +tags for Gmail, lowercase)
- [ ] [T064C] Link payment_transactions.meal_plan_id after meal_plan creation (initially NULL, updated after successful AI generation)
- [ ] [T065] Implement quiz_responses polling logic (10 retries × 500ms) to handle race conditions per FR-P-008
- [ ] [T066] Create manual_resolution queue entry creation for missing quiz data at `backend/src/services/manual_resolution.py`

**Acceptance**: Webhook signature verified, payment_transactions record created with all metadata, duplicate webhooks return 200 without reprocessing, missing quiz data routes to manual queue

### 6.4 AI Meal Plan Generation

- [ ] [T067] Setup OpenAI Agents SDK client configuration at `backend/src/lib/ai_client.py` with environment-based model selection (Gemini dev, OpenAI prod) per research.md lines 67-80
- [ ] [T068] Create Pydantic models for AI structured output at `backend/src/schemas/ai_output.py`: Meal, DayMealPlan, MealPlanOutput
- [ ] [T069] Create AI agent meal plan generator at `backend/src/services/meal_plan_generator.py` with Agent, Runner.run(), 30-day prompt (research.md lines 94-153)
- [ ] [T070] Implement keto compliance validation: check each day <30g carbs, retry up to 2 times on failure per FR-A-007
- [ ] [T071] Implement structural integrity validation: verify 30 days, 3 meals per day, all fields populated, retry up to 1 time per FR-A-015
- [ ] [T072] Implement AI retry logic with exponential backoff (2s, 4s, 8s) and Gemini fallback on auth/quota errors per FR-A-011
- [ ] [T073] Add 20-second timeout to AI generation call using asyncio.wait_for()

**Acceptance**: AI generates 30-day plan <20s, keto compliance validated, structural validation passes, retries work, manual queue triggered on failure

### 6.5 PDF Generation (ReportLab)

- [ ] [T074] Create PDF generator service at `backend/src/services/pdf_generator.py` using ReportLab with cover page, 30-day meals table, 4 weekly shopping lists (research.md lines 651-787)
- [ ] [T075] Implement custom PDF styles with green theme (#22c55e), table layouts, macronutrient breakdown per meal
- [ ] [T076] Add 20-second timeout to PDF generation with error handling
- [ ] [T077] Create PDF validation to ensure file generated successfully (non-zero bytes, valid PDF header)

**Acceptance**: PDF generated <20s, includes cover + 30 days + shopping lists, green theme applied, file size 400-600KB

### 6.6 Vercel Blob Storage

- [ ] [T078] Create Vercel Blob upload service at `backend/src/services/blob_storage.py` with on-demand signed URL generation function (generates fresh 1-hour signed URL when called, not pre-generated) (FR-D-005, FR-D-006, FR-R-003)
- [ ] [T079] Implement PDF upload to Vercel Blob with random suffix for filename collision prevention
- [ ] [T080] Store permanent blob path (not time-limited signed URL) in meal_plans.pdf_blob_path field with status update to "completed"

**Acceptance**: PDF uploaded to Vercel Blob, permanent blob path stored in database (not signed URL), on-demand function can generate fresh signed URLs with 1-hour expiry throughout 90-day retention period

### 6.7 Email Delivery (Resend)

- [ ] [T081] Create delivery email template at `backend/src/templates/delivery_email.html` with green theme, PDF attachment, recovery instructions (FR-E-003)
- [ ] [T082] Implement email sending with Resend at `backend/src/services/email_service.py` with PDF attachment + download link to /api/download-pdf endpoint (generates fresh signed URL on-demand per FR-E-002)
- [ ] [T083] Add email retry logic (3 attempts, exponential backoff 2s, 4s, 8s) and failure routing to manual_resolution queue
- [ ] [T084] Update meal_plans.email_sent_at timestamp on successful delivery
- [ ] [T085] Implement email idempotency check to prevent duplicate sends on webhook retries

**Acceptance**: Email delivered with PDF attachment <90s total from payment, retries on failure, manual queue triggered if all attempts fail

### 6.8 Orchestration (Background Task)

- [ ] [T086] Create meal plan delivery orchestration at `backend/src/services/delivery_orchestrator.py` coordinating AI → PDF → Blob → Email flow
- [ ] [T087] Add transaction boundaries: atomic quiz save + meal_plan creation, atomic payment update + AI trigger, atomic PDF + email delivery per FR-Q-018
- [ ] [T088] Implement rollback handling for each transaction boundary with retry capability
- [ ] [T089] Add comprehensive error logging with Sentry integration for each step failure

**Acceptance**: Full flow completes in <90s (p95), errors logged to Sentry, transactions rollback on failure, retries work correctly

### 6.9 Integration Testing (Payment & AI Pipeline)

- [ ] [T089A] Write integration tests for email verification at `backend/tests/integration/test_email_verification.py`: code generation, 10-min expiry, resend cooldown (60s), Redis storage, rate limiting (8 test cases)
- [ ] [T089B] Write integration tests for Paddle webhook handler at `backend/tests/integration/test_paddle_webhooks.py`: HMAC-SHA256 validation, timestamp check (5-min window), idempotency via payment_id unique constraint, quiz polling (10 retries × 500ms), manual resolution routing (12 test cases)
- [ ] [T089C] Write integration tests for payment lock at `backend/tests/integration/test_payment_locks.py`: Redis SETNX acquisition, 60s TTL, duplicate payment prevention (10-min window), lock release on completion (6 test cases)
- [ ] [T089D] Write integration tests for AI generation at `backend/tests/integration/test_ai_generation.py`: mock OpenAI/Gemini responses, keto compliance validation (<30g carbs), structural validation (30 days, 3 meals each), retry logic (2 keto retries, 1 structural retry), fallback to Gemini (10 test cases)
- [ ] [T089E] Write integration tests for PDF generation at `backend/tests/integration/test_pdf_generator.py`: ReportLab output structure, 30 days + 4 weekly shopping lists, macronutrient tables, file size 400-600KB validation (5 test cases)
- [ ] [T089F] Write integration tests for Vercel Blob upload at `backend/tests/integration/test_blob_storage.py`: mock HTTP upload, signed URL generation, random suffix collision prevention, error handling (4 test cases)
- [ ] [T089G] Write integration tests for email delivery at `backend/tests/integration/test_email_service.py`: Resend API mock, PDF attachment handling, retry logic (3 attempts with backoff), idempotency check (6 test cases)
- [ ] [T089H] Write E2E test for full pipeline at `backend/tests/e2e/test_meal_plan_pipeline.py`: webhook received → AI generation → PDF creation → Blob upload → Email sent, verify <90s total completion, test with 3 different quiz profiles (weight loss, muscle gain, maintenance)
- [ ] [T089I] Perform manual testing: 5 complete purchase flows with varied quiz data (different genders, activity levels, food preferences), verify AI output quality (9/10 keto compliance per SC-004), test duplicate payment prevention, verify email delivery with PDF attachment

**Acceptance**: All integration tests pass (51+ test cases), E2E pipeline test completes in <90s, manual testing achieves 5/5 successful deliveries with 9/10 AI quality

---

## Phase 7: User Story 4 (P3) - PDF Recovery via Account or Magic Link

### 7.1 Magic Link Generation

- [ ] [T090] [US4] Create magic link token generator at `backend/src/services/magic_link.py` with 256-bit entropy, SHA256 hash storage (research.md lines 1074-1140)
- [ ] [T091] [US4] Implement rate limiting (3 requests per email per 24h) using Redis counters
- [ ] [T092] [US4] Create public recovery page at `frontend/src/pages/recover-plan.tsx` with email input form
- [ ] [T093] [US4] Create recovery API endpoint `POST /api/recovery/request-magic-link` at `backend/src/api/recovery.py` with 5 requests per IP per hour rate limit

**Acceptance**: Magic link generated, email sent with 24h expiry link, rate limits enforced, recovery page accessible

### 7.2 Magic Link Verification

- [ ] [T094] [US4] Create magic link verification endpoint `GET /api/recovery/verify?token=` at `backend/src/api/recovery.py`
- [ ] [T095] [US4] Implement single-use enforcement: set used_at timestamp, reject subsequent uses
- [ ] [T096] [US4] Add IP address logging (generation_ip, usage_ip) with mismatch warning but not blocking
- [ ] [T097] [US4] Create PDF download page at `frontend/src/pages/download.tsx` showing plan details and download button

**Acceptance**: Magic link works once, expires after 24h, second use rejected with clear error, IP mismatch logged but allowed

### 7.3 Optional Account Creation

- [ ] [T098] Create account registration endpoint `POST /api/auth/register` at `backend/src/api/auth.py` with email verification, password hashing
- [ ] [T099] [US4] Create account creation prompt on success page at `frontend/src/components/quiz/SuccessPage.tsx` with Skip option
- [ ] [T100] Add account creation link to delivery email with signed token encoding purchase_email
- [ ] [T101] Enforce account email must match purchase email (readonly field, pre-filled) per FR-R-001

**Acceptance**: User creates account post-purchase, email must match purchase, account accessible for login, Skip option works

### 7.4 Account Dashboard

- [ ] [T102] [US4] Create login endpoint `POST /api/auth/login` at `backend/src/api/auth.py` with JWT token generation
- [ ] [T103] [US4] Create dashboard page at `frontend/src/pages/dashboard.tsx` showing meal plan details, PDF download button, expiry countdown
- [ ] [T104] [US4] Implement download availability status display: "X days remaining of 90-day retention"

**Acceptance**: User logs in, dashboard shows meal plan, download button works, expiry countdown accurate

### 7.5 Download Rate Limiting

- [ ] [T105] [US4] Create download rate limiter at `backend/src/lib/rate_limiting.py` using Redis TTL keys, composite identifier (user_id or email+IP hash), 10 downloads per 24h (research.md lines 1207-1305)
- [ ] [T106] [US4] Implement 5-minute grace period exclusion after PDF delivery (allows immediate downloads)
- [ ] [T107] [US4] Create download endpoint `GET /api/download-pdf` with rate limit check, then generate fresh signed URL on-demand from blob path, return redirect or signed URL (FR-R-003, FR-E-002)

**Acceptance**: Authenticated users limited by user_id, magic link users by email+IP, first 5 min excluded, limit exceeded shows hours until reset, fresh signed URL generated on each download request (1-hour expiry)

### 7.6 Integration Testing (Recovery & Accounts)

- [ ] [T107A] Write unit tests for magic link generation at `backend/tests/unit/test_magic_link.py`: 256-bit token entropy verification, SHA256 hashing, expiry timestamp calculation (24h), rate limit (3 per email per 24h) (8 test cases)
- [ ] [T107B] Write integration tests for magic link flow at `backend/tests/integration/test_magic_link_flow.py`: generation with Redis storage, verification with token hash lookup, single-use enforcement (used_at timestamp), expiry validation, IP logging with mismatch warning (10 test cases)
- [ ] [T107C] Write integration tests for account creation at `backend/tests/integration/test_account_creation.py`: email match enforcement (readonly field), password hashing with bcrypt, signup token validation (signed JWT), account creation at 3 touchpoints (mid-quiz, post-purchase, email link) (8 test cases)
- [ ] [T107D] Write integration tests for download rate limiting at `backend/tests/integration/test_download_limits.py`: authenticated users (Redis key with user_id), magic link users (Redis key with email+IP hash), 10 downloads per 24h limit, 5-minute grace period after delivery, TTL key expiration (12 test cases)
- [ ] [T107E] Write integration tests for recovery API at `backend/tests/integration/test_recovery_api.py`: public recovery page requests, normalized_email lookup, 5 requests per IP per hour rate limit, email enumeration prevention (generic success messages), magic link delivery (6 test cases)
- [ ] [T107F] Perform manual testing: PDF recovery via magic link (verify single-use, test expiry at 24h, test IP mismatch warning), account creation at all 3 touchpoints, dashboard login and PDF download, download rate limit enforcement (attempt 11th download)

**Acceptance**: All tests pass (44+ test cases), magic link single-use verified, rate limits enforced correctly, manual testing 6/6 scenarios successful, no email enumeration possible

---

## Phase 8: User Story 5 (P3) - Smooth UI Animations & Loading States

### 8.1 Framer Motion Transitions

- [ ] [T108] [US5] Add Framer Motion animations to QuizContainer for step transitions (300-400ms ease-in-out)
- [ ] [T109] [US5] Create animated LoadingScreen component at `frontend/src/components/LoadingScreen.tsx` with multi-step progress messages
- [ ] [T110] [US5] Implement success confirmation animation on SuccessPage with scale effect on download button
- [ ] [T111] [US5] Add skeleton loaders to dashboard while fetching meal plan data

**Acceptance**: Step transitions smooth 60fps, loading messages animate sequentially, success page scales smoothly, no jank on mobile

---

## Phase 9: Security & Automation

### 9.1 Mid-Quiz Signup (Hybrid Auth)

- [ ] [T112] Create mid-quiz signup prompt at `frontend/src/components/quiz/SaveProgressModal.tsx` appearing after Step 10 per FR-Q-020
- [ ] [T113] Implement incremental quiz saves for authenticated users at `backend/src/api/quiz.py` endpoint `POST /api/quiz/save-progress`
- [ ] [T114] Add cross-device resume logic: load last saved step from database on authenticated user login
- [ ] [T115] Display device warning on quiz start page: "Your quiz progress is saved only on this device. Create account during quiz to save across devices."

**Acceptance**: Prompt shows after Step 10, account creation works, incremental saves enable cross-device sync, unauthenticated users continue with localStorage

### 9.2 Chargeback Handling

- [ ] [T116] Create chargeback webhook handler at `backend/src/api/webhooks/paddle.py` endpoint for `payment.chargeback` event
- [ ] [T116A] Update payment_transactions.payment_status to "chargeback" for payment_id (FR-P-013)
- [ ] [T117] Add normalized_email to email_blacklist table with 90-day TTL on chargeback
- [ ] [T118] Log chargeback event with payment_id, email, timestamp, reason to Sentry
- [ ] [T119] Update blacklist check in checkout flow to query email_blacklist using normalized_email

**Acceptance**: Chargeback webhook processes, payment_transactions status updated, email blacklisted for 90 days, future purchases blocked with message

### 9.3 Refund Abuse Prevention

- [ ] [T120] Add refund count tracking to meal_plans table (refund_count column default 0)
- [ ] [T120A] Update payment_transactions.payment_status to "refunded" for payment_id on refund webhook (FR-P-013)
- [ ] [T121] Implement refund pattern detection at `backend/src/services/refund_guard.py`: ≥2 refunds in 90d flags 3rd purchase for manual review per FR-P-011
- [ ] [T122] Create manual review flag in manual_resolution queue with issue_type="repeat_refund_user"
- [ ] [T123] Add 30-day purchase block for users with ≥3 refunds in 90 days

**Acceptance**: Refund count incremented, payment_transactions status updated, 3rd purchase flagged for manual review, 3+ refunds blocked with support message

### 9.4 SLA Monitoring & Auto-Refund

- [ ] [T124] Create SLA monitoring job at `scripts/sla_monitor.py` running every 15 minutes checking manual_resolution.sla_deadline
- [ ] [T125] Implement Paddle refund API integration at `backend/src/services/paddle_refunds.py` with payment method compatibility check per FR-P-012
- [ ] [T126] Add automatic refund trigger on SLA miss (4 hours) with email notification
- [ ] [T127] Update manual_resolution status to "sla_missed_refunded" and log high-priority Sentry alert

**Acceptance**: Job runs every 15 min, SLA breaches detected, automatic refund triggered, manual methods route to manual_resolution

### 9.5 Integration Testing (Security & Automation)

- [ ] [T127A] Write integration tests for mid-quiz signup at `backend/tests/integration/test_mid_quiz_signup.py`: account creation at Step 10 prompt, email verification during signup, incremental quiz saves to database, cross-device resume capability (load last saved step) (6 test cases)
- [ ] [T127B] Write integration tests for chargeback handling at `backend/tests/integration/test_chargeback.py`: webhook event processing, normalized_email blacklisting with 90-day TTL, blacklist lookup during checkout, Sentry alert verification (6 test cases)
- [ ] [T127C] Write integration tests for refund abuse prevention at `backend/tests/integration/test_refund_abuse.py`: refund_count tracking per normalized_email, ≥2 refunds flagging 3rd purchase for manual review, ≥3 refunds blocking with 30-day lockout, manual_resolution queue entry creation (8 test cases)
- [ ] [T127D] Write integration tests for SLA monitoring at `backend/tests/integration/test_sla_monitoring.py`: scheduled job execution every 15 min, sla_deadline breach detection, Paddle refund API call (mocked), payment method compatibility check, auto-refund vs manual_resolution routing (8 test cases)
- [ ] [T127E] Write integration tests for manual resolution queue at `backend/tests/integration/test_manual_queue.py`: queue entry creation (missing quiz data, AI failure, email failure), status transitions (pending → in_progress → resolved), Sentry alerts on creation, SLA tracking (6 test cases)
- [ ] [T127F] Perform manual testing: trigger manual resolution scenarios (delete quiz_responses before webhook, force AI timeout, disable Resend API), verify SLA monitoring job detects breaches, test refund abuse detection (simulate 3 refunds), verify chargeback blacklisting

**Acceptance**: All tests pass (34+ test cases), SLA job runs on schedule, auto-refund triggers correctly, refund abuse patterns detected, manual testing 5/5 scenarios route to correct resolution path

### 9.6 Admin Dashboard for Manual Resolution

- [ ] [T127G] Create admin authentication middleware at `backend/src/middleware/admin_auth.py` with API key validation (X-API-Key header vs ADMIN_API_KEY env var) + IP whitelist check (ADMIN_IP_WHITELIST env var) per FR-M-005
- [ ] [T127H] Create admin dashboard endpoint `GET /admin/manual-resolution` at `backend/src/api/admin.py` returning manual_resolution queue entries (pending, in_progress, escalated) with SLA countdown
- [ ] [T127I] Create admin dashboard UI at `frontend/src/pages/admin/manual-resolution.tsx` showing pending count, time to SLA breach, quick actions (mark resolved, trigger manual PDF generation, issue refund)
- [ ] [T127J] Implement quick action endpoints: `POST /admin/manual-resolution/{id}/resolve`, `POST /admin/manual-resolution/{id}/regenerate`, `POST /admin/manual-resolution/{id}/refund`

**Acceptance**: Admin can access dashboard with valid API key + whitelisted IP, sees pending queue entries with SLA countdown, can execute quick actions (resolve, regenerate, refund), unauthorized requests return 401

---

## Phase 10: Monitoring, Cleanup & Deploy

### 10.1 Cleanup Jobs (Data Retention)

- [ ] [T128] Create paid quiz responses cleanup job at `scripts/cleanup_paid_quiz.py` deleting records where pdf_delivered_at < NOW() - 24h, runs every 6 hours
- [ ] [T129] Create unpaid quiz responses cleanup job at `scripts/cleanup_unpaid_quiz.py` deleting records where created_at < NOW() - 7d AND payment_id IS NULL, runs daily
- [ ] [T130] Create meal plan metadata cleanup job at `scripts/cleanup_meal_plans.py` deleting records where created_at < NOW() - 90d, runs daily
- [ ] [T131] Create PDF blob cleanup job at `scripts/cleanup_pdfs.py` deleting blobs where created_at < NOW() - 91d (90d + 24h grace), runs daily at 00:00 UTC
- [ ] [T132] Create magic link token cleanup job at `scripts/cleanup_magic_links.py` deleting expired tokens, runs daily
- [ ] [T133] Create email blacklist cleanup job at `scripts/cleanup_blacklist.py` deleting expired entries, runs daily
- [ ] [T133A] Create payment transactions cleanup job at `scripts/cleanup_payment_transactions.py` deleting records where created_at < NOW() - 1y (compliance/audit retention), runs monthly
- [ ] [T134] Log all deletions to Sentry for compliance audit trail

**Acceptance**: All cleanup jobs run on schedule, data retention policy enforced (including 1-year payment_transactions retention per FR-P-013), deletions logged with timestamps

### 10.2 Monitoring & Alerts

- [ ] [T135] [P] Configure Sentry alerts for error rate >5%, payment failures, manual queue entries, AI failures >2 consecutive
- [ ] [T136] [P] Setup Vercel Analytics for performance monitoring with p95 latency tracking
- [ ] [T137] [P] Create Vercel Blob storage monitoring dashboard tracking usage approaching 80% of 5GB free tier
- [ ] [T138] [P] Configure webhook timestamp validation failure alerts (>3 per hour triggers Sentry email)

**Acceptance**: Alerts trigger correctly, email notifications sent to project owner, dashboards accessible

### 10.3 Production Deployment

- [ ] [T139] Create production environment variables in Vercel dashboard (frontend) and Render dashboard (backend)
- [ ] [T140] Configure Vercel deployment for Next.js frontend with custom domain
- [ ] [T141] Deploy FastAPI backend to Render (Web Service with uvicorn)
- [ ] [T142] Run Alembic migrations against production Neon DB
- [ ] [T143] Configure cleanup cron jobs in Render dashboard (cleanup-paid-quiz, cleanup-pdfs, cleanup-magic-links, check-sla-breaches)

**Acceptance**: Production deployment live (Frontend: Vercel, Backend: Render), all services running, environment variables configured, cron jobs scheduled

### 10.4 End-to-End Testing & Production Verification

- [ ] [T144] Write E2E test suite at `backend/tests/e2e/test_complete_journey.py`: Full user journey from quiz start to PDF recovery, test 3 scenarios (weight loss female sedentary, muscle gain male very active, maintenance female moderately active), verify each completes in <90s
- [ ] [T145] Write load test script at `scripts/load_test.py`: Simulate 10 concurrent quiz submissions using pytest-xdist or locust, measure p95 completion time, verify database handles concurrent writes, Redis locks prevent race conditions
- [ ] [T146] Write security test suite at `backend/tests/security/test_security.py`: Webhook replay attack prevention (timestamp validation), rate limit bypass attempts (Redis counters), SQL injection in quiz inputs (parameterized queries), XSS in dietary restrictions field (sanitization), magic link brute force (256-bit entropy) (12 test cases)
- [ ] [T147] Perform manual testing with 10+ quiz variations: Test all combinations: 2 genders × 5 activity levels × 3 goals, vary food preferences (minimum 10 items, maximum selections, all categories empty except required), verify AI keto compliance (9/10 plans must pass <30g carbs per SC-004)
- [ ] [T148] Test all 9 edge cases from spec.md: (1) Submit quiz without email, (2) AI API failure with retry/fallback, (3) Payment webhook with missing quiz data, (4) Email delivery failure with retry, (5) User navigates back after payment, (6) Blob storage at 80% capacity, (7) Contradictory food preferences, (8) Page refresh during quiz, (9) Calorie calculation below minimum (1200F/1500M)
- [ ] [T149] Verify all 12 success criteria (SC-001 to SC-012): Quiz completion >70%, payment success >95%, PDF delivery >98%, AI keto compliance 100%, email delivery >99%, PDF recovery >90%, uptime >99.5%, p95 performance (<90s journey, <20s AI, <20s PDF, <500ms queries), mobile UX (no scroll, 44px buttons), security (zero breaches, data deleted), cost efficiency (within free tiers)
- [ ] [T150] Production smoke tests in live environment: Health check endpoint returns 200, database connection verified, Redis PING succeeds, Sentry test error logged with email alert, Vercel Blob test upload successful, Resend test email delivered, Paddle webhook test event processed

**Acceptance**: E2E tests pass 3/3 journeys in <90s, load test achieves <90s p95 with 10 concurrent users, security tests pass 12/12, manual testing confirms 9/10 AI quality, all 9 edge cases handled correctly, all 12 success criteria met, production smoke tests 7/7 pass

---

## Dependency Diagram

```
Phase 1: Project Setup & Infrastructure
├── T001-T005: Repository Structure (parallel)
├── T006-T009: Dependencies Installation (parallel, after T001-T005)
└── T010-T013: Database & External Services (after T006-T009)
    ↓
Phase 2: Foundational Data Layer
├── T014-T019: Database Models (parallel, after T010)
├── T020-T022: Migrations (after T014-T019)
├── T023-T026: Core Utilities (parallel, after T010)
├── T027-T029: Base API Router (after T020, T023)
└── T029A-T029E: Unit & Integration Testing (after T027-T029)
    ↓
Phase 3: User Story 1 - Complete Quiz End-to-End
├── T030-T036: Quiz UI Components (parallel, after T001)
├── T037-T039: Quiz State Management (after T030-T036)
├── T040-T042: Quiz Backend API (after T027, T023, T024)
└── T043-T045: Review Screen (after T039, T040)
    ↓
Phase 4: User Story 2 - Navigate Backward
└── T046-T048: Back Button Logic (after T037)
    ↓
Phase 5: User Story 3 - Privacy Messaging
└── T049-T052: Privacy UI Components (parallel, after T030)
    ↓
Phase 6: Payment & AI Generation (CRITICAL PATH)
├── T053-T056: Email Verification (after T027, T056 parallel to T030)
├── T057-T061: Paddle Integration (after T040, T053)
├── T062-T066: Webhook Handler (after T027, T023)
├── T067-T073: AI Generation (after T027, T062)
├── T074-T077: PDF Generation (after T073)
├── T078-T080: Vercel Blob Storage (after T074)
├── T081-T085: Email Delivery (after T078)
├── T086-T089: Orchestration (after T067-T085)
└── T089A-T089I: Integration Testing (after T086-T089)
    ↓
Phase 7: User Story 4 - PDF Recovery
├── T090-T093: Magic Link Generation (parallel, after T027)
├── T094-T097: Magic Link Verification (after T090)
├── T098-T101: Account Creation (parallel, after T027)
├── T102-T104: Account Dashboard (after T098)
├── T105-T107: Download Rate Limiting (after T094, T102)
└── T107A-T107F: Integration Testing (after T105-T107)
    ↓
Phase 8: User Story 5 - Smooth Animations
└── T108-T111: Framer Motion Transitions (parallel, after T030, T043)
    ↓
Phase 9: Security & Automation
├── T112-T115: Mid-Quiz Signup (after T037, T098)
├── T116-T119: Chargeback Handling (after T062)
├── T120-T123: Refund Abuse Prevention (after T062)
├── T124-T127: SLA Monitoring (after T066, T086)
└── T127A-T127F: Integration Testing (after T124-T127)
    ↓
Phase 10: Monitoring, Cleanup & Deploy
├── T128-T134: Cleanup Jobs (parallel, after T020)
├── T135-T138: Monitoring & Alerts (parallel, after T027)
├── T139-T143: Production Deployment (after ALL previous tasks)
└── T144-T150: E2E Testing & Production Verification (after T139-T143)
```

---

## Task Summary

**Total Tasks**: 176 (145 implementation + 31 testing)
**Estimated Time**: 88 hours (176 tasks × 30 min average)
**Critical Path**: Phase 1 → Phase 2 → Phase 3 → Phase 6 → Phase 10 (MVP delivery)
**Parallelizable Tasks**: 41 tasks (marked with [P])

**Testing Tasks Distribution**:
- Phase 2.5 (Data Layer): 5 tasks (unit + integration)
- Phase 6.9 (Payment & AI): 9 tasks (integration + E2E + manual)
- Phase 7.6 (Recovery): 6 tasks (unit + integration + manual)
- Phase 9.5 (Security): 6 tasks (integration + manual)
- Phase 10.4 (Production): 7 tasks (E2E + load + security + manual)

**User Story Distribution**:
- US1 (P1 - Complete Quiz): 23 tasks
- US2 (P2 - Back Navigation): 3 tasks
- US3 (P2 - Privacy): 4 tasks
- US4 (P3 - Recovery): 18 tasks
- US5 (P3 - Animations): 4 tasks
- Infrastructure/Security: 93 tasks
- **Testing**: 31 tasks

---

## Acceptance Criteria (Overall)

### Functional Requirements Coverage
- [ ] All 54 functional requirements (FR-Q-001 to FR-U-013) implemented
- [ ] All 5 user stories completed with acceptance scenarios passing
- [ ] All 9 edge cases handled with documented behavior

### Performance Targets (FR-F-001 to FR-F-005)
- [ ] Full journey (Quiz → Payment → AI → PDF → Email) <90s (p95)
- [ ] AI meal plan generation <20s (p95)
- [ ] PDF generation <20s (p95)
- [ ] Database queries <500ms (p95)
- [ ] Frontend quiz load <3s on mobile 3G

### Success Criteria (SC-001 to SC-012)
- [ ] Quiz completion rate >70%
- [ ] Payment success rate >95%
- [ ] PDF delivery success >98%
- [ ] AI keto compliance 100%
- [ ] Email delivery rate >99%
- [ ] PDF recovery success >90%
- [ ] System uptime >99.5%
- [ ] Mobile UX: no horizontal scroll, all buttons ≥44px
- [ ] Security: zero breaches, health data deleted after delivery
- [ ] Cost efficiency: stay within free tiers

### Data Retention Compliance
- [ ] Quiz responses (paid) deleted 24h after PDF delivery
- [ ] Quiz responses (unpaid) deleted 7 days after submission
- [ ] Biometric data deleted 24h after delivery
- [ ] Meal plan metadata retained 90 days
- [ ] PDFs deleted 91 days after creation (90d + 24h grace)
- [ ] Manual resolution entries retained 1 year
- [ ] All deletions logged for audit

---

## Implementation Notes

### Development Workflow
1. **Setup Phase**: Complete Phase 1-2 before any feature work
2. **MVP Priority**: Focus on Critical Path (Phases 1, 2, 3, 6) for fastest time-to-market
3. **Testing Strategy**: Manual testing for quiz flows, pytest for backend services
4. **Deployment**: Incremental Vercel deployments after each phase completion

### Key Technical Decisions (from research.md)
- **AI**: OpenAI Agents SDK with `set_default_openai_client()`, Gemini dev/OpenAI prod
- **PDF**: ReportLab for programmatic generation with precise layout control
- **Storage**: Vercel Blob with native signed URLs (5GB free tier)
- **Payments**: Paddle with ALL payment methods enabled (cards, Apple/Google Pay, local methods)
- **Email**: Resend with retry logic and idempotency
- **Locks**: Redis SETNX for distributed payment locks
- **Rate Limiting**: Redis TTL keys for download/recovery limits
- **Normalization**: Gmail dot/plus removal for blacklist bypass prevention

### Constitution Compliance Checklist
- [x] Principle I: Personalization via AI (20-step quiz, JSONB preferences)
- [x] Principle II: Full automation (payment webhook → AI → PDF → email)
- [x] Principle III: Privacy-first (24h/90d deletion, Paddle PCI, HTTPS)
- [x] Principle IV: Keto compliance (<30g carbs validation, retry on failure)
- [x] Principle V: Reliability (manual resolution queue, 4h SLA, auto-refund)
- [x] Principle VI: Cost-effective (free tiers, 80% monitoring)
- [x] Principle VII: Type safety (TypeScript strict, Pydantic, Zod)
- [x] Principle VIII: UX excellence (Keto Creator patterns, mobile-first 360px)
- [x] Principle IX: Performance monitoring (Sentry, Vercel Analytics, SLA tracking)
- [x] Principle X: Accurate calories (Mifflin-St Jeor, activity multipliers, floors)

---

**Next Steps**: Begin implementation with Phase 1 tasks T001-T013. Run `/sp.implement` to execute tasks in dependency order.

