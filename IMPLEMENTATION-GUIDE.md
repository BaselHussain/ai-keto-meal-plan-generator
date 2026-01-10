# Implementation Guide: Keto Meal Plan Generator

**Branch**: `001-keto-meal-plan-generator`
**Last Updated**: 2026-01-01 (Spec v1.3.0 - Gap Resolution)
**Status**: Ready for Implementation

## Recent Updates (2026-01-01)

This guide has been updated to reflect clarifications from spec.md v1.3.0 (Session 2026-01-01):

1. **Email Verification**: 24-hour verified status validity (allows Paddle modal abandonment)
2. **Blob Storage**: On-demand signed URL generation (prevents expiry mismatch during 90-day retention)
3. **Admin Dashboard**: New tasks T127G-T127J for admin authentication (API key + IP whitelist)
4. **Accepted Risks**: Gmail-only normalization, Redis lock race condition (documented in tasks.md)

---

## Tech Stack Overview

### Frontend (Vercel)
```
Next.js 14.x + TypeScript 5.x
├── React 18.2 (UI components)
├── React Hook Form 7.50 (form state management)
├── Zod 3.22 (validation schemas)
├── Tailwind CSS 3.4 (styling)
├── Framer Motion 11.0 (animations)
├── Lucide React 0.323 (icons)
└── Paddle.js 1.2 (payment UI)
```

### Backend (Render)
```
FastAPI + Python 3.11+
├── Uvicorn 0.27 (ASGI server)
├── SQLAlchemy 2.0 (ORM, async)
├── Alembic 1.13 (migrations)
├── Pydantic 2.6 (data validation)
├── OpenAI Agents SDK >=0.1.0 (AI generation)
├── ReportLab 4.0 (PDF generation)
├── python-jose 3.3 (JWT auth)
├── bcrypt 4.1 (password hashing)
└── httpx 0.26 (async HTTP client)
```

### Infrastructure
```
Database: Neon DB (serverless PostgreSQL 15+)
Cache/Locks: Redis 7.x (Upstash/Redis Cloud)
Blob Storage: Vercel Blob (5GB free tier)
Email: Resend API
Payment: Paddle (checkout + webhooks)
Monitoring: Sentry (error tracking)
```

---

## Sub-Agent & Skill Reference

### Available Sub-Agents (9 Total)

| Agent | Domain | Primary Tasks |
|-------|--------|---------------|
| **backend-engineer** | FastAPI setup, coordination | T001-T010, T139-T143 (deployment) |
| **database-engineer** | SQLAlchemy, Alembic, API endpoints | T011-T088, T089A-T107F |
| **payment-webhook-engineer** | Paddle integration, webhooks | T030-T038, T092-T097, T144 |
| **email-auth-engineer** | Resend, magic links, JWT | T039-T049, T050-T055, T108-T115 |
| **data-retention-engineer** | Cleanup jobs, SLA monitoring | T116-T120, T128-T138, T143, T149-T150 |
| **ai-specialist** | OpenAI Agents SDK, meal plans | T090-T091, T107A-T107F |
| **pdf-designer** | ReportLab PDF generation | T098-T106, T107A-T107F |
| **security-auditor** | Security audits, penetration tests | Security reviews after each phase |
| **frontend-engineer** | Next.js, React, UI/UX | T121-T126, T127A-T127F, T139-T140 |

### Available Skills (14 Total)

| Skill | Command | Purpose |
|-------|---------|---------|
| Test Suite | `/test` | Run unit/integration/E2E tests |
| Database Migration | `/migrate` | Alembic migration management |
| Environment Setup | `/setup-env` | Validate env vars and API connections |
| AI Validation | `/validate-ai` | Test AI meal plan generation |
| PDF Validation | `/validate-pdf` | Test PDF structure and rendering |
| Webhook Testing | `/test-webhook` | Simulate Paddle webhooks |
| Deploy | `/deploy` | Deploy to Vercel + Render |
| Monitor | `/monitor` | System health monitoring |
| Cleanup | `/cleanup` | Run data retention jobs |
| SLA Check | `/check-sla` | Check manual resolution queue |
| Seed Data | `/seed-data` | Seed test database |
| Email Test | `/test-email` | Send test email via Resend |
| Security Audit | `/audit-security` | Run security audit |
| Blacklist Check | `/check-blacklist` | Email blacklist management |

---

## Phase-by-Phase Implementation Flow

### Phase 0: Pre-Implementation Setup

**Duration**: 1-2 hours
**Prerequisites**: None

#### Tasks
- [ ] Clone repository and checkout `001-keto-meal-plan-generator` branch
- [ ] Read all specs: `spec.md`, `plan.md`, `tasks.md`, `quickstart.md`, `DEPLOYMENT-ARCHITECTURE.md`
- [ ] Review constitution: `.specify/memory/constitution.md`

#### Sub-Agents
- None (manual review)

#### Skills
- `/setup-env check` - Verify all required tools installed (Node 18+, Python 3.11+, Docker)

#### Acceptance Criteria
- ✅ All spec files reviewed and understood
- ✅ Development tools installed
- ✅ Git branch checked out

---

### Phase 1: Project Setup & Infrastructure

**Duration**: 2-3 hours
**Tasks**: T001-T013 (13 tasks)

#### Sub-Agent Assignment

**backend-engineer** (T001-T010):
- T001: Initialize frontend and backend directory structure
- T002: Set up Git repository with `.gitignore` for secrets
- T003: Create `frontend/package.json` with Next.js 14.x dependencies
- T004: Create `backend/requirements.txt` with FastAPI dependencies
- T005: Install frontend dependencies (`pnpm install`)
- T006: Install backend dependencies (`pip install -r requirements.txt`)
- T007: Initialize FastAPI app with CORS, Sentry, health check endpoint
- T008: Create `.env.local` template for frontend
- T009: Create `.env` template for backend with all required variables
- T010: Document secrets in `quickstart.md` (already done ✅)

**database-engineer** (T011-T013):
- T011: Set up Neon DB project and copy connection string
- T012: Initialize Alembic (`alembic init database/migrations`)
- T013: Configure Redis connection (local Docker or Upstash)

#### Skills to Use

```bash
# After T001-T006
/setup-env create    # Generate .env templates

# After T007
/monitor             # Verify FastAPI health endpoint works

# After T011-T013
/migrate create "initial schema"  # Test Alembic setup
```

#### Testing (Before Phase 2)

```bash
# Verify infrastructure
/setup-env check     # All env vars present
/monitor             # DB + Redis + FastAPI responding

# Manual checks
- [ ] Frontend dev server starts: `pnpm dev` → http://localhost:3000
- [ ] Backend dev server starts: `uvicorn src.main:app --reload` → http://localhost:8000
- [ ] FastAPI docs accessible: http://localhost:8000/docs
- [ ] Database connection successful
- [ ] Redis ping successful
```

**Quality Gate**: ✅ All infrastructure services running, no connection errors

---

### Phase 2: Database Models & Migrations

**Duration**: 4-5 hours
**Tasks**: T014-T028 + T029A-T029E (20 tasks)

#### Sub-Agent Assignment

**database-engineer** (T014-T029E):

**Data Models** (T014-T023):
- T014: Create `User` model (email, normalized_email, created_at)
- T015: Create `QuizResponse` model (20-step data, JSONB, timestamps)
- T016: Create `MealPlan` model (payment_id, preferences_summary JSONB, pdf_url)
- T016A: Create `PaymentTransaction` model (payment_id, amount, currency, payment_method, payment_status - FR-P-013)
- T017: Create `ManualResolution` model (queue entries, SLA tracking)
- T018: Create `MagicLinkToken` model (secure tokens, single-use, expiry)
- T019: Create `EmailBlacklist` model (normalized_email, 90d TTL)
- T020: Add indexes on `normalized_email`, `payment_id`, `created_at`
- T021: Add JSONB GIN indexes for `preferences_summary` querying
- T022: Generate initial Alembic migration (`alembic revision --autogenerate`)
- T023: Apply migration (`alembic upgrade head`)

**Utilities** (T024-T028):
- T024: Implement email normalization (Gmail dots, plus tags, case)
- T025: Implement Mifflin-St Jeor calorie calculator
- T026: Implement activity multiplier logic (sedentary to athlete)
- T027: Implement calorie floor enforcement (1200 women, 1500 men)
- T028: Create database session factory (async SQLAlchemy)

**Unit Tests** (T029A-T029E):
- T029A: Test email normalization (10 test cases)
- T029B: Test calorie calculator (12 test cases)
- T029C: Test database CRUD operations (8 test cases)
- T029D: Test JSONB schema validation (6 test cases)
- T029E: Test index performance with `EXPLAIN ANALYZE` (5 queries)

#### Skills to Use

```bash
# After T014-T021
/migrate create "add database models"  # Generate migration

# After T022-T023
/migrate up          # Apply migration
/monitor detailed    # Verify all tables created

# After T024-T028
/seed-data           # Seed test data to verify models work

# After T029A-T029E
/test unit           # Run unit tests (80%+ coverage required)
```

#### Testing Gate (Before Phase 3)

```bash
# Run all unit tests
/test unit

# Verify data layer
/seed-data           # Should create users, quiz, meal plans
psql $DATABASE_URL -c "\dt"  # Verify all 7 tables exist (including payment_transactions)
psql $DATABASE_URL -c "\di"  # Verify indexes created

# Performance check
/test unit test_email_utils.py      # Email normalization: <1ms
/test unit test_calorie_calculator.py  # Calorie calc: <1ms
/test unit test_database_crud.py    # DB operations: <500ms
```

**Quality Gate**: ✅ 80%+ test coverage, all migrations applied, indexes verified, seed data works

---

### Phase 3: Payment Webhooks & Email Verification

**Duration**: 6-8 hours
**Tasks**: T030-T049 (20 tasks)

#### Sub-Agent Assignment

**payment-webhook-engineer** (T030-T038 + T064A-T064C):
- T030: Implement Paddle checkout session creation
- T031: Create `POST /webhooks/paddle` endpoint
- T032: Implement HMAC-SHA256 signature verification
- T033: Implement timestamp replay attack prevention (±5min)
- T034: Create Redis distributed lock mechanism (`SETNX`)
- T035: Implement idempotency logic for duplicate webhooks
- T036: Build payment state machine (pending → completed)
- T037: Implement refund/chargeback handlers
- T038: Add payment event audit logging (Sentry)
- T064A-T064C: Store payment transaction metadata (amount, currency, payment_method - FR-P-013)

**email-auth-engineer** (T039-T049):
- T039: Implement email normalization in verification flow
- T040: Create 6-digit verification code generator (crypto-random)
- T041: Store verification code in Redis (10min code expiry, 24h verified status validity)
- T042: Create `POST /quiz/verify-email` endpoint
- T043: Implement Resend email sending function
- T044: Create verification email template (HTML + plain text)
- T045: Implement verification code validation (3 attempts max)
- T046: Implement rate limiting (3 emails/hour per address)
- T047: Add email to blacklist on 3 failed verification attempts
- T048: Track verified status separately from code (24h validity allows Paddle modal abandonment)
- T049: Add email verification audit logging

#### Skills to Use

```bash
# After T030
/test-webhook payment-success  # Test Paddle checkout

# After T031-T038
/test-webhook payment-success  # Simulate payment.succeeded
/test-webhook chargeback       # Test chargeback handling
/audit-security               # Check webhook security

# After T039-T049
/test-email test@resend.dev   # Send verification email
/check-blacklist list         # Verify blacklist functionality
```

#### Testing (After Phase 3)

**No formal testing gate** - continue to Phase 4. Testing happens in Phase 6.

**Quick validation**:
```bash
# Webhook validation
/test-webhook payment-success
/monitor detailed  # Check webhook processed

# Email validation
/test-email test@resend.dev
# Check Resend dashboard for delivery
```

---

### Phase 4: Quiz API Endpoints

**Duration**: 5-6 hours
**Tasks**: T050-T065 (16 tasks)

#### Sub-Agent Assignment

**database-engineer** (T050-T065):

**Authentication** (T050-T055):
- T050: Create `POST /auth/magic-link/request` endpoint
- T051: Generate 256-bit secure magic link token
- T052: Store token in `MagicLinkToken` table (24h expiry)
- T053: Send magic link email via Resend
- T054: Create `POST /auth/magic-link/verify` endpoint
- T055: Implement JWT token generation on successful verification

**Quiz Endpoints** (T056-T065):
- T056: Create `POST /quiz/submit` endpoint (all 20 steps)
- T057: Validate quiz payload with Pydantic schema (20 fields)
- T058: Calculate calorie target using Mifflin-St Jeor
- T059: Store quiz response in `QuizResponse` table
- T060: Implement quiz retrieval endpoint (for pre-payment display)
- T061: Add rate limiting to quiz submission (1/min per IP)
- T062: Implement quiz expiry (7 days for unpaid, 24h for paid)
- T063: Add quiz submission audit logging
- T064: Create `POST /quiz/checkout` endpoint (Paddle session)
- T065: Link quiz response to pending payment

#### Skills to Use

```bash
# After T050-T055
/test-email test@resend.dev  # Test magic link email
/audit-security              # Check token security

# After T056-T065
/seed-data                   # Create quiz test data
/monitor detailed            # Verify API endpoints
```

#### Testing (After Phase 4)

**No formal testing gate** - continue to Phase 5. Testing happens in Phase 6.

**Quick validation**:
```bash
# Test quiz submission
curl -X POST http://localhost:8000/v1/quiz/submit \
  -H "Content-Type: application/json" \
  -d @test-quiz-payload.json

# Verify rate limiting
/audit-security  # Should block >1 req/min
```

---

### Phase 5: Meal Plan & Checkout Endpoints

**Duration**: 4-5 hours
**Tasks**: T066-T076 (11 tasks)

#### Sub-Agent Assignment

**database-engineer** (T066-T076):
- T066: Create `GET /meal-plans/{payment_id}` endpoint
- T067: Implement meal plan retrieval with auth validation
- T068: Create `POST /internal/generate-meal-plan` (webhook-triggered)
- T069: Validate payment before generation
- T070: Extract preferences from `QuizResponse`
- T071: Add generation timestamp and metadata
- T072: Update `MealPlan` table with generation status
- T073: Implement checkout session creation with Paddle
- T074: Store Paddle transaction ID in `MealPlan`
- T075: Return checkout URL to frontend
- T076: Add checkout audit logging

#### Skills to Use

```bash
# After T066-T076
/seed-data                   # Create meal plan test data
/test-webhook payment-success  # Trigger generation pipeline
/monitor detailed            # Verify meal plan created
```

#### Testing (After Phase 5)

**No formal testing gate** - continue to Phase 6.

---

### Phase 6: Internal Endpoints & Integration Testing

**Duration**: 6-8 hours
**Tasks**: T077-T088 + T089A-T089I (21 tasks)

#### Sub-Agent Assignment

**database-engineer** (T077-T088):
- T077: Create `POST /internal/send-email` endpoint
- T078: Implement email delivery via Resend
- T079: Create `POST /internal/upload-pdf` endpoint
- T080: Implement Vercel Blob upload with signed URLs
- T081: Add PDF metadata to `MealPlan` table
- T082: Create pipeline orchestrator (payment → AI → PDF → email)
- T083: Implement retry logic with exponential backoff
- T084: Add failure handling → manual resolution queue
- T085: Create `GET /internal/health` comprehensive health check
- T086: Implement Redis connection check
- T087: Implement Neon DB connection check
- T088: Implement Vercel Blob connectivity check

**Integration Tests** (T089A-T089I):

**database-engineer + email-auth-engineer**:
- T089A: Test email verification flow (8 test cases)
- T089B: Test rate limiting enforcement (6 test cases)
- T089C: Test email blacklist (4 test cases)
- T089D: Test quiz submission with calorie calculation (10 test cases)
- T089E: Test quiz expiry (paid vs unpaid)
- T089F: Test checkout session creation
- T089G: Test webhook → generation trigger
- T089H: Test internal pipeline orchestration
- T089I: Test failure → manual queue routing

#### Skills to Use

```bash
# After T077-T088
/monitor detailed            # Test all health checks
/test-email test@resend.dev  # Test email delivery
/validate-pdf                # Test PDF upload

# Integration testing
/test integration            # Run all integration tests
/audit-security              # Security review
```

#### Testing Gate (Before Phase 7) 🚦

**CRITICAL CHECKPOINT** - Must pass before AI/PDF implementation

```bash
# Run full integration test suite
/test integration

# Required test results:
- [ ] T089A: Email verification (8/8 passed)
- [ ] T089B: Rate limiting (6/6 passed)
- [ ] T089C: Email blacklist (4/4 passed)
- [ ] T089D: Quiz + calorie calc (10/10 passed)
- [ ] T089E: Quiz expiry (2/2 passed)
- [ ] T089F: Checkout session (1/1 passed)
- [ ] T089G: Webhook trigger (1/1 passed)
- [ ] T089H: Pipeline orchestration (1/1 passed)
- [ ] T089I: Manual queue routing (1/1 passed)

# Health checks
/monitor detailed
- [ ] FastAPI responding (<500ms)
- [ ] Neon DB connected
- [ ] Redis connected
- [ ] Vercel Blob accessible
- [ ] Resend API working

# Security audit
/audit-security
- [ ] Rate limiting enforced
- [ ] SQL injection protection
- [ ] XSS sanitization
- [ ] CORS configured correctly
- [ ] Webhook signature validation

# Coverage requirement
/test integration --cov
- [ ] 80%+ code coverage
```

**Quality Gate**: ✅ All integration tests pass, health checks green, security audit clean, 80%+ coverage

---

### Phase 7: AI Generation, Payment Testing & PDF Generation

**Duration**: 8-10 hours
**Tasks**: T090-T106 + T107A-T107F (23 tasks)

#### Sub-Agent Assignment

**ai-specialist** (T090-T091):
- T090: Design OpenAI Agents SDK meal plan agent architecture
- T091: Implement meal plan generation with dynamic system prompts

**payment-webhook-engineer** (T092-T097):
- T092: Write unit tests for webhook signature validation
- T093: Write integration tests for webhook pipeline
- T094: Test distributed lock under concurrent webhooks
- T095: Test idempotency with duplicate payloads
- T096: Test refund/chargeback processing
- T097: End-to-end payment flow test

**pdf-designer** (T098-T106):
- T098: Design PDF layout with ReportLab (30-day calendar)
- T099: Implement PDF header with branding
- T100: Implement daily meal plan sections (3 meals/day)
- T101: Implement macro breakdown tables
- T102: Implement shopping list generation
- T103: Implement PDF footer with generation timestamp
- T104: Generate PDF and upload to Vercel Blob (store permanent blob path, not signed URL)
- T105: Create on-demand signed URL generation function (generates fresh 1-hour URLs when called)
- T106: Add PDF generation to pipeline orchestrator

**Integration Tests** (T107A-T107F):

**database-engineer + ai-specialist + pdf-designer**:
- T107A: Test AI meal plan generation (5 scenarios)
- T107B: Test keto compliance validation (<30g carbs)
- T107C: Test AI retry on failure (3 attempts)
- T107D: Test PDF generation with all sections
- T107E: Test full pipeline (payment → AI → PDF → email)
- T107F: Test manual queue on AI/PDF failure

#### Skills to Use

```bash
# AI validation
/validate-ai weight-loss     # Test weight loss meal plan
/validate-ai muscle-gain     # Test muscle gain meal plan
/validate-ai maintenance     # Test maintenance meal plan

# Payment testing
/test-webhook payment-success
/test-webhook chargeback
/test-webhook refund

# PDF validation
/validate-pdf                # Test PDF structure

# Full pipeline test
/test integration
```

#### Testing Gate (Before Phase 8) 🚦

**CRITICAL CHECKPOINT** - AI/PDF/Payment must work end-to-end

```bash
# AI validation (must pass 9/10 quality threshold)
/validate-ai weight-loss     # Should generate valid plan
/validate-ai muscle-gain     # Should generate valid plan
/validate-ai maintenance     # Should generate valid plan

# Quality checks for each plan:
- [ ] <30g carbs/day (keto compliance)
- [ ] Calorie target ±100 calories
- [ ] 3 meals/day × 30 days = 90 meals
- [ ] Macro breakdown: 70% fat, 25% protein, 5% carbs
- [ ] No excluded foods present
- [ ] Preferred proteins prioritized

# PDF validation
/validate-pdf
- [ ] 30-day calendar rendered correctly
- [ ] All meals present with recipes
- [ ] Shopping list generated (grouped by category)
- [ ] Macro breakdown table accurate
- [ ] Branding and footer present

# Payment integration tests
/test integration test_payment_webhook.py
- [ ] T092: Signature validation (3/3 passed)
- [ ] T093: Webhook pipeline (1/1 passed)
- [ ] T094: Distributed lock (2/2 passed)
- [ ] T095: Idempotency (3/3 passed)
- [ ] T096: Refund/chargeback (2/2 passed)
- [ ] T097: E2E payment (1/1 passed)

# Full pipeline test (T107A-T107F)
/test integration test_full_pipeline.py
- [ ] T107A: AI generation (5/5 scenarios passed)
- [ ] T107B: Keto compliance (10/10 plans <30g carbs)
- [ ] T107C: AI retry logic (3/3 attempts)
- [ ] T107D: PDF generation (1/1 passed)
- [ ] T107E: Full pipeline (1/1 passed, <90s)
- [ ] T107F: Manual queue on failure (2/2 passed)

# Performance validation
- [ ] AI generation: <20s (p95)
- [ ] PDF generation: <20s (p95)
- [ ] Full pipeline: <90s (p95)

# Manual testing scenarios (10 required)
- [ ] Test with beef allergy (should exclude beef)
- [ ] Test with vegetarian preference (eggs/fish only)
- [ ] Test with nut allergy (no nuts in recipes)
- [ ] Test extreme calorie (1200 floor enforced)
- [ ] Test extreme calorie (3500 athlete)
- [ ] Test concurrent payment webhooks (no duplicates)
- [ ] Test webhook signature failure (401 returned)
- [ ] Test AI generation failure (queued for manual)
- [ ] Test PDF generation failure (queued for manual)
- [ ] Test Resend email failure (retry logic works)
```

**Quality Gate**: ✅ AI quality 9/10+, PDF renders correctly, payment tests pass, pipeline <90s, manual queue works

---

### Phase 8: Recovery API & Manual Resolution Queue

**Duration**: 6-8 hours
**Tasks**: T108-T120 + T127G-T127J (17 tasks)

#### Sub-Agent Assignment

**email-auth-engineer** (T108-T115):
- T108: Create `POST /recovery/request-link` endpoint
- T109: Validate email exists in `MealPlan` table
- T110: Generate secure recovery token (256-bit)
- T111: Store token in Redis (24h expiry)
- T112: Send recovery email with magic link
- T113: Implement rate limiting (3 requests/hour)
- T114: Create `GET /recovery/download/{token}` endpoint (generates fresh signed URL on-demand)
- T115: Return PDF signed URL after token validation

**data-retention-engineer** (T116-T120):
- T116: Create `ManualResolution` queue model (already done in T017)
- T117: Implement queue entry creation on pipeline failure
- T118: Add SLA timestamp calculation (4-hour deadline)
- T119: Create `GET /internal/manual-queue` endpoint for admin
- T120: Implement queue filtering by SLA status

**backend-engineer + frontend-engineer** (T127G-T127J - Admin Dashboard):
- T127G: Create admin authentication middleware (API key + IP whitelist per FR-M-005)
- T127H: Create admin dashboard endpoint `GET /admin/manual-resolution`
- T127I: Create admin dashboard UI showing pending queue, SLA countdown
- T127J: Implement quick action endpoints (resolve, regenerate, refund)

#### Skills to Use

```bash
# Recovery testing
/test-email test@resend.dev  # Test recovery email
/check-blacklist list        # Verify rate limiting

# Manual queue
/check-sla                   # Check for SLA breaches
/monitor detailed            # Verify queue entries
```

#### Testing (After Phase 8)

**No formal testing gate** - continue to Phase 9. Testing happens in Phase 10.

---

### Phase 9: Frontend Implementation

**Duration**: 8-10 hours
**Tasks**: T121-T126 + T127A-T127F (12 tasks)

#### Sub-Agent Assignment

**frontend-engineer** (T121-T126):
- T121: Create multi-step quiz component (20 steps)
- T122: Implement form validation with React Hook Form + Zod
- T123: Create payment integration with Paddle.js
- T124: Implement results page with PDF download
- T125: Create recovery page (request + download)
- T126: Implement error handling and loading states

**Frontend Tests** (T127A-T127F):

**frontend-engineer + email-auth-engineer**:
- T127A: Test quiz form validation (20 fields)
- T127B: Test step navigation (forward/back)
- T127C: Test payment redirect to Paddle
- T127D: Test PDF download after payment
- T127E: Test recovery flow (request + download)
- T127F: Test mobile responsiveness (360px width)

#### Skills to Use

```bash
# Frontend development
pnpm dev  # Start dev server at http://localhost:3000

# Testing
/test e2e  # Run end-to-end tests with Playwright
```

#### Testing Gate (Before Phase 10) 🚦

**CRITICAL CHECKPOINT** - Frontend must integrate with backend APIs

```bash
# Frontend tests
/test e2e

# Required test results:
- [ ] T127A: Quiz validation (20/20 fields)
- [ ] T127B: Step navigation (forward/back)
- [ ] T127C: Payment redirect (Paddle modal)
- [ ] T127D: PDF download (successful)
- [ ] T127E: Recovery flow (email + download)
- [ ] T127F: Mobile responsive (360px-768px)

# Manual E2E testing (Critical User Journeys)
1. Complete Quiz → Payment → AI Generation → PDF Email (Full Happy Path)
   - [ ] Start quiz at http://localhost:3000
   - [ ] Fill all 20 steps (valid data)
   - [ ] Submit and verify email
   - [ ] Complete payment (Paddle sandbox)
   - [ ] Wait for email (<90s)
   - [ ] Download PDF from email link
   - [ ] Verify PDF content (30 days, macros, shopping list)

2. Recovery Flow (PDF Re-download)
   - [ ] Navigate to /recovery
   - [ ] Enter email used in test 1
   - [ ] Receive recovery email
   - [ ] Click magic link
   - [ ] Download PDF successfully

3. Error Scenarios
   - [ ] Invalid email format (should show validation error)
   - [ ] Duplicate payment attempt (should prevent with lock)
   - [ ] Expired quiz (should show expiry message)
   - [ ] Rate limit exceeded (should show "try again later")

# Performance validation (Frontend)
- [ ] Lighthouse score >90 (Performance)
- [ ] Lighthouse score >90 (Accessibility)
- [ ] First Contentful Paint <1.5s
- [ ] Time to Interactive <3.5s

# Browser compatibility
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)
```

**Quality Gate**: ✅ All E2E tests pass, user journeys work, Lighthouse >90, mobile responsive

---

### Phase 10: Data Retention, Deployment & Final Testing

**Duration**: 6-8 hours
**Tasks**: T128-T150 (23 tasks)

#### Sub-Agent Assignment

**data-retention-engineer** (T128-T143):

**Cleanup Jobs** (T128-T133A):
- T128: Create `cleanup_paid_quiz.py` script (6-hour cron)
- T129: Create `cleanup_pdfs.py` script (daily cron)
- T130: Create `cleanup_magic_links.py` script (daily cron)
- T131: Implement Vercel Blob deletion logic
- T132: Implement database soft deletion with audit logging
- T133: Add Sentry logging for cleanup events
- T133A: Create `cleanup_payment_transactions.py` script (monthly cron, 1-year retention - FR-P-013)

**SLA Monitoring** (T134-T138):
- T134: Create `sla_monitor.py` script (15-min cron)
- T135: Query `ManualResolution` for entries >4 hours old
- T136: Send Sentry alert for SLA breaches
- T137: Send email notification to support team
- T138: Update queue entry with alert timestamp

**Deployment** (T139-T143):

**backend-engineer + frontend-engineer + data-retention-engineer**:
- T139: Create production env vars (Vercel + Render dashboards)
- T140: Deploy Next.js frontend to Vercel
- T141: Deploy FastAPI backend to Render (Web Service)
- T142: Run Alembic migrations against production Neon DB
- T143: Configure Render cron jobs (cleanup + SLA monitoring)

**Final Testing** (T144-T150):

**All agents (coordinated)**:
- T144: Full payment flow E2E test in production
- T145: Test all 10+ quiz variations (allergies, preferences, goals)
- T146: Verify data retention (quiz deleted after 24h)
- T147: Verify PDF retention (deleted after 90 days)
- T148: Test manual resolution queue with real failure
- T149: Verify cron job execution (check Render logs)
- T150: Test SLA monitoring (create entry >4h old)

#### Skills to Use

```bash
# Cleanup job testing (local)
/cleanup dry-run             # Preview what will be deleted
/cleanup force               # Execute cleanup

# SLA monitoring
/check-sla                   # Check for breaches
/check-sla alert             # Send test alert

# Deployment
/deploy staging              # Deploy to staging first
/deploy production           # Deploy to production

# Post-deployment validation
/monitor detailed            # Check all services
/test e2e                    # Run E2E tests against production
```

#### Final Testing Gate (Before Launch) 🚦

**CRITICAL CHECKPOINT** - Production readiness validation

```bash
# 1. Cleanup job validation
/cleanup dry-run
- [ ] Identifies correct records for deletion
- [ ] Respects retention periods (24h quiz, 90d PDF)
- [ ] Logs deletions to Sentry

/cleanup force
- [ ] Deletes from database successfully
- [ ] Deletes from Vercel Blob successfully
- [ ] No orphaned records

# 2. SLA monitoring validation
/check-sla
- [ ] Identifies entries >4h old
- [ ] Sends Sentry alert
- [ ] Sends email to support team
- [ ] Updates alert timestamp

# 3. Cron job validation (Render dashboard)
- [ ] cleanup-paid-quiz runs every 6 hours
- [ ] cleanup-pdfs runs daily at 00:00 UTC
- [ ] cleanup-magic-links runs daily at 02:00 UTC
- [ ] check-sla-breaches runs every 15 minutes
- [ ] All cron jobs show "success" status

# 4. Production deployment checklist
Frontend (Vercel):
- [ ] Environment variables set (NEXT_PUBLIC_API_URL, Paddle keys)
- [ ] Custom domain configured (optional)
- [ ] Build succeeds
- [ ] https://keto-meal-plan.vercel.app accessible

Backend (Render):
- [ ] Environment variables set (all 15+ variables)
- [ ] Build command: pip install + alembic upgrade head
- [ ] Start command: uvicorn src.main:app --host 0.0.0.0 --port $PORT
- [ ] Health check: /health returns 200
- [ ] https://keto-meal-plan-api.onrender.com/health accessible

Database (Neon DB):
- [ ] Production branch created
- [ ] Connection pooling enabled
- [ ] Backups configured (daily)
- [ ] All migrations applied

# 5. Production E2E test (T144)
/test e2e --env production

Full user journey:
- [ ] Complete quiz on production URL
- [ ] Verify email (real Resend email)
- [ ] Complete payment (Paddle production mode)
- [ ] Receive PDF email (<90s)
- [ ] PDF download works
- [ ] PDF content correct (30 days, keto compliant)

# 6. Quiz variation testing (T145) - 10+ scenarios
- [ ] Weight loss + beef allergy → No beef in plan
- [ ] Muscle gain + vegetarian → Eggs/fish only
- [ ] Maintenance + nut allergy → No nuts
- [ ] Weight loss + sedentary → 1200-1500 cal
- [ ] Muscle gain + athlete → 2500-3500 cal
- [ ] Exclude: beef, pork, dairy → Plan complies
- [ ] Prefer: chicken, salmon → High frequency
- [ ] Dietary restriction: "No shellfish" → Complies
- [ ] Behavioral: "No breakfast" → 2 meals/day
- [ ] Medical: "Diabetic" → Extra low carb

Each scenario must achieve:
- [ ] AI quality score 9/10+
- [ ] Keto compliance <30g carbs/day
- [ ] Calorie target ±100 calories
- [ ] All exclusions/preferences respected

# 7. Data retention testing (T146-T147)
- [ ] Paid quiz deleted after 24 hours
- [ ] Unpaid quiz deleted after 7 days
- [ ] PDF deleted after 90 days
- [ ] Vercel Blob cleanup successful
- [ ] Audit logs captured in Sentry

# 8. Manual resolution testing (T148)
- [ ] Force AI generation failure (invalid API key)
- [ ] Verify entry added to manual queue
- [ ] Verify SLA timestamp set (4h deadline)
- [ ] Admin can view queue at /internal/manual-queue
- [ ] Sentry alert triggered

# 9. Performance validation (Production)
Full pipeline latency:
- [ ] Payment webhook processing: <2s (p95)
- [ ] AI generation: <20s (p95)
- [ ] PDF generation: <20s (p95)
- [ ] Email delivery: <10s (p95)
- [ ] Total pipeline: <90s (p95)

API endpoints:
- [ ] POST /quiz/submit: <500ms (p95)
- [ ] POST /quiz/verify-email: <1s (p95)
- [ ] POST /webhooks/paddle: <2s (p95)
- [ ] GET /meal-plans/{id}: <300ms (p95)

# 10. Security audit (Production)
/audit-security --env production

- [ ] Rate limiting enforced (all endpoints)
- [ ] Webhook signature validation (Paddle)
- [ ] SQL injection protection (parameterized queries)
- [ ] XSS sanitization (input validation)
- [ ] CORS restricted to production domain
- [ ] HTTPS enforced (no HTTP)
- [ ] Secrets not exposed in logs/errors
- [ ] JWT tokens expire after 7 days
- [ ] Magic links expire after 24 hours
- [ ] Email blacklist prevents abuse

# 11. Monitoring & alerting
Sentry dashboard:
- [ ] Error tracking enabled
- [ ] Email alerts configured for:
  - [ ] Error rate >5%
  - [ ] SLA breaches (manual queue >4h)
  - [ ] Payment webhook failures
  - [ ] AI generation failures
  - [ ] PDF generation failures

Vercel Analytics:
- [ ] Page views tracked
- [ ] Conversion funnel visible
- [ ] Performance metrics collected

# 12. Cost monitoring
- [ ] Neon DB usage <80% of free tier
- [ ] Vercel Blob usage <80% of 5GB
- [ ] Resend emails <80% of daily limit
- [ ] Redis usage monitored
- [ ] OpenAI API costs tracked
```

**Quality Gate**: ✅ All production tests pass, 10+ quiz variations work, cleanup jobs run, SLA monitoring active, security audit clean

---

## Testing Summary by Phase

| Phase | Testing Required | Skills | Quality Gate |
|-------|------------------|--------|--------------|
| **Phase 1** | Infrastructure validation | `/setup-env`, `/monitor` | ✅ All services running |
| **Phase 2** | Unit tests (80%+ coverage) | `/test unit`, `/seed-data` | ✅ All models work, migrations applied |
| **Phase 3-5** | Quick validation only | `/test-webhook`, `/test-email` | None (test in Phase 6) |
| **Phase 6** | Integration tests (critical) | `/test integration`, `/audit-security` | ✅ 80%+ coverage, security clean |
| **Phase 7** | AI/PDF/Payment tests | `/validate-ai`, `/validate-pdf`, `/test integration` | ✅ 9/10 quality, pipeline <90s |
| **Phase 9** | E2E frontend tests | `/test e2e` | ✅ All user journeys work, Lighthouse >90 |
| **Phase 10** | Production readiness | `/deploy`, `/monitor`, `/check-sla`, `/cleanup` | ✅ All production tests pass |

---

## Implementation Timeline Estimate

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 0: Pre-setup | 1-2 hours | 2 hours |
| Phase 1: Infrastructure | 2-3 hours | 5 hours |
| Phase 2: Database + Tests | 4-5 hours | 10 hours |
| Phase 3: Webhooks + Email | 6-8 hours | 18 hours |
| Phase 4: Quiz API | 5-6 hours | 24 hours |
| Phase 5: Meal Plan API | 4-5 hours | 29 hours |
| Phase 6: Internal + Integration Tests | 6-8 hours | 37 hours |
| Phase 7: AI + PDF + Payment Tests | 8-10 hours | 47 hours |
| Phase 8: Recovery + Queue + Admin Dashboard | 6-8 hours | 55 hours |
| Phase 9: Frontend + E2E Tests | 8-10 hours | 65 hours |
| Phase 10: Cleanup + Deployment | 6-8 hours | 71 hours |

**Total Estimated Time**: **60-71 hours** (7-9 days for solo developer)

---

## Quality Standards Throughout

### Code Quality
- ✅ TypeScript strict mode (frontend)
- ✅ Type hints on all Python functions (backend)
- ✅ Pydantic models for all API contracts
- ✅ Zod schemas for all form validation
- ✅ No `any` types in TypeScript
- ✅ No bare `except:` in Python
- ✅ Explicit error handling with custom exceptions

### Testing Standards
- ✅ 80%+ code coverage (unit + integration)
- ✅ All edge cases tested
- ✅ Performance tests for critical paths
- ✅ Security tests for all auth/payment flows
- ✅ E2E tests for all user journeys

### Performance Standards
- ✅ API latency <500ms (p95)
- ✅ Database queries <500ms
- ✅ AI generation <20s (p95)
- ✅ PDF generation <20s (p95)
- ✅ Full pipeline <90s (p95)
- ✅ Frontend Lighthouse >90

### Security Standards
- ✅ All secrets in environment variables
- ✅ HTTPS enforced
- ✅ CORS restricted
- ✅ Rate limiting on all public endpoints
- ✅ SQL injection protection (parameterized queries)
- ✅ XSS sanitization (input validation)
- ✅ Webhook signature validation
- ✅ JWT/magic link expiration enforced

---

## Emergency Contacts & Resources

### Documentation
- **Spec**: `specs/001-keto-meal-plan-generator/spec.md`
- **Architecture**: `specs/001-keto-meal-plan-generator/DEPLOYMENT-ARCHITECTURE.md`
- **Quickstart**: `specs/001-keto-meal-plan-generator/quickstart.md`
- **Tasks**: `specs/001-keto-meal-plan-generator/tasks.md`
- **Constitution**: `.specify/memory/constitution.md`

### Skills Reference
- **All Skills**: `.claude/skills/README.md`
- **Testing**: `.claude/skills/test/SKILL.md`
- **Deployment**: `.claude/skills/deploy/SKILL.md`
- **Monitoring**: `.claude/skills/monitor/SKILL.md`

### External APIs
- **Paddle Docs**: https://developer.paddle.com
- **OpenAI Agents SDK**: https://github.com/openai/openai-agents-python
- **Resend Docs**: https://resend.com/docs
- **Vercel Blob**: https://vercel.com/docs/storage/vercel-blob
- **Neon DB**: https://neon.tech/docs

---

## Next Steps

**You are here**: Ready to start Phase 1 (Project Setup & Infrastructure)

**To begin implementation**:
```bash
# 1. Verify prerequisites
/setup-env check

# 2. Invoke backend-engineer for Phase 1
# (Start with Tasks T001-T010)

# 3. Then invoke database-engineer for database setup
# (Tasks T011-T013)

# 4. Run testing gate before Phase 2
/monitor
/setup-env check
```

**Remember**:
- Use appropriate sub-agent for each task
- Run skills for validation and testing
- Respect testing gates before moving to next phase
- Maintain 80%+ code coverage
- Document all architectural decisions

**Good luck! 🚀**
