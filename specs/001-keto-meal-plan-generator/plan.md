# Implementation Plan: AI-Powered Personalized Keto Meal Plan Generator

**Branch**: `001-keto-meal-plan-generator` | **Date**: 2025-12-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-keto-meal-plan-generator/spec.md`

**Note**: This document is filled in by the `/sp.plan` command execution workflow.

## Summary

Build a full-stack SaaS application that guides users through a 20-step quiz to collect personalized health data, food preferences, and behavioral patterns, then automatically generates a customized 30-day keto meal plan delivered via PDF email within 90 seconds. The system combines Next.js (frontend), FastAPI (backend), Paddle (payments), OpenAI Agents SDK (AI generation), Neon DB (PostgreSQL), Vercel Blob (PDF storage), and Resend (email) to deliver a privacy-first, automated, and keto-compliant user experience with robust security controls.

## Technical Context

**Language/Version**: TypeScript 5.x (Next.js 14.x frontend), Python 3.11+ (FastAPI backend)

**Primary Dependencies**:
- **Frontend**: Next.js 14.x, React Hook Form, Zod, Tailwind CSS, Framer Motion, React Icons/Lucide, Paddle.js
- **Backend**: FastAPI, Pydantic, SQLAlchemy, OpenAI Agents SDK (>=0.1.0,<1.0.0), ReportLab, Uvicorn
- **AI**: OpenAI Agents SDK with AsyncOpenAI client (OpenAI production, Gemini dev via custom base_url)

**Storage**: Neon DB (serverless PostgreSQL), Vercel Blob (PDF storage, 5GB free tier), Redis (distributed locks, rate limiting)

**Testing**: Manual testing priority for MVP (10+ quiz variations, AI quality 9/10 pass), pytest for backend

**Target Platform**: Web (Frontend: Vercel hosting, Backend: Render hosting)

**Project Type**: Web application (Next.js frontend + FastAPI backend)

**Performance Goals**: Full journey <90s (p95), AI <20s, PDF <20s, DB queries <500ms

**Constraints**: Free tier optimization, keto compliance (<30g carbs/day), privacy-first (24h data deletion), security (email verification, webhook validation, duplicate prevention, rate limiting)

**Scale/Scope**: MVP launch, 20-step quiz, 30-day meal plans (3 meals/day), 90-day PDF retention, hybrid auth

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Principle I: Personalization Through AI-Driven Insights
- **Status**: PASS - 20-step quiz, AI prompts with user parameters, JSONB preferences

### ✅ Principle II: Full Automation from Quiz to Delivery
- **Status**: PASS - Automated pipeline, idempotent webhooks, retry logic

### ✅ Principle III: Privacy-First Data Management
- **Status**: PASS - Data retention policy, 24h/90d deletion, Paddle PCI, HTTPS, env secrets

### ✅ Principle IV: Keto Compliance Guarantee
- **Status**: PASS - <30g carbs/day validation, macro breakdown, AI retry on failure

### ✅ Principle V: Reliability and Quality Standards
- **Status**: PASS - Performance targets, 9/10 quality, manual resolution queue

### ✅ Principle VI: Cost-Effective Development
- **Status**: PASS - Free tiers (Neon, Vercel Blob 5GB, Resend), monitoring at 80%

### ✅ Principle VII: Type Safety and Code Quality
- **Status**: PASS - TypeScript strict, Pydantic models, Zod schemas, explicit error handling

### ✅ Principle VIII: User Experience Excellence
- **Status**: PASS - Keto Creator UX patterns, mobile-first 360px, PDF recovery

### ✅ Principle IX: Performance and Monitoring
- **Status**: PASS - Sentry error tracking, Vercel Analytics, email alerts

### ✅ Principle X: Accurate Calorie Estimation
- **Status**: PASS - Mifflin-St Jeor formula, activity multipliers, calorie floors

**GATE RESULT**: ✅ **PASS** - All 10 principles satisfied. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-keto-meal-plan-generator/
├── plan.md              # This file (/sp.plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── quiz-api.yaml
│   ├── payment-webhooks.yaml
│   ├── ai-generation.yaml
│   └── recovery-api.yaml
└── tasks.md             # Phase 2 (/sp.tasks - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/                # SQLAlchemy ORM
│   ├── services/              # Business logic
│   ├── api/                   # FastAPI endpoints
│   ├── lib/                   # Utilities
│   └── main.py
└── tests/

frontend/
├── src/
│   ├── components/            # Quiz, Payment, Recovery, Dashboard
│   ├── pages/                 # Next.js pages
│   ├── services/              # API calls
│   ├── lib/                   # Validators
│   └── types/
└── tests/

database/
└── migrations/                # SQLAlchemy Alembic

scripts/                       # Cleanup jobs (cron)

.github/workflows/             # CI/CD
```

**Structure Decision**: Web application. Frontend (Next.js TS) for quiz UI + validation. Backend (FastAPI Python) for webhooks, AI, PDF, email, manual resolution. Redis for locks + rate limits. Neon DB for persistence.

## Complexity Tracking

> **No constitution violations - section intentionally empty**

---

## Phase 0: Research

**Objective**: Resolve all technical unknowns and research best practices for key integrations.

**Research Topics**:
1. OpenAI Agents SDK integration with FastAPI async workflows (Runner.run(), function_tool decorators)
2. Vercel Blob signed URL generation and security (time-limited tokens, non-guessable URLs)
3. Paddle webhook HMAC-SHA256 + timestamp validation (signature verification, replay prevention)
4. Redis distributed lock patterns for concurrent payment prevention (SETNX, TTL, lock release)
5. Email normalization patterns (Gmail dot/plus removal, blacklist bypass prevention)
6. ReportLab PDF generation with complex layouts (30 days + tables + shopping lists)
7. Mifflin-St Jeor formula implementation (men/women equations, activity multipliers, calorie floors)
8. Neon DB JSONB schema design for preferences_summary (querying, indexing, validation)
9. Magic link security patterns (256-bit tokens, single-use enforcement, IP logging, expiration)
10. Redis rate limiting implementation (TTL keys, composite identifiers, exclusion windows)

**Output**: ✅ `research.md` (47.8 KB) - All decisions documented with rationale, alternatives, and implementation patterns.

---

## Phase 1: Design & Contracts

**Prerequisites**: Phase 0 research.md complete ✅

**Objectives**:
1. Extract entities from feature spec → `data-model.md` ✅
2. Generate API contracts from functional requirements → `/contracts/` ✅
3. Create `quickstart.md` with setup instructions ✅
4. Update agent context (`.specify/scripts/bash/update-agent-context.sh claude`) ✅

**Entities Modeled**:
- User (email, normalized_email, account creation timestamp)
- QuizResponse (20-step data, temporary 24h/7d retention)
- MealPlan (payment_id, metadata, PDF URL, preferences_summary JSONB, 90d retention)
- ManualResolution (queue entries, SLA tracking, 1-year retention)
- MagicLinkToken (secure tokens, single-use, 24h expiry)
- EmailBlacklist (normalized_email, 90-day TTL)

**API Contracts Created**:
- `quiz-api.yaml` - Quiz submission, email verification, checkout (FR-Q-001 to FR-Q-020)
- `payment-webhooks.yaml` - Paddle webhook processing (FR-P-002, FR-P-008, FR-M-001 to FR-M-006)
- `ai-generation.yaml` - Internal AI service with retry policies (FR-A-001 to FR-A-015)
- `recovery-api.yaml` - Magic links, PDF downloads, rate limiting (FR-R-001 to FR-R-005)

**Output**: ✅ `data-model.md` (20.1 KB), `contracts/` (4 files, 37.4 KB), `quickstart.md` (11.3 KB), updated `CLAUDE.md`

---

## Next Steps

**Phase 2: Tasks Generation** (separate command - NOT part of `/sp.plan`)
- Run `/sp.tasks` to generate dependency-ordered implementation tasks
- Tasks will be created in `tasks.md` with acceptance criteria and test cases
- Each task will reference specific FR requirements and include implementation guidance

**Total Planning Artifacts Created**: 7 files (117 KB documentation) ready for implementation.
