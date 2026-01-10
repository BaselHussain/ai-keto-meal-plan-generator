---
id: 0012
title: Keto Meal Plan Implementation Planning
stage: plan
date: 2025-12-29
surface: agent
model: claude-sonnet-4-5
feature: 001-keto-meal-plan-generator
branch: 001-keto-meal-plan-generator
user: Basel Hussain
command: /sp.plan
labels: ["planning", "architecture", "phase-0", "phase-1", "sdd-workflow"]
links:
  spec: specs/001-keto-meal-plan-generator/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-keto-meal-plan-generator/plan.md
  - specs/001-keto-meal-plan-generator/research.md
  - specs/001-keto-meal-plan-generator/data-model.md
  - specs/001-keto-meal-plan-generator/quickstart.md
  - specs/001-keto-meal-plan-generator/contracts/api.yaml
tests:
  - none (planning phase - implementation artifacts only)
---

## Prompt

/sp.plan

User provided detailed implementation milestones:
- **Phase 1 (Foundation)**: Quiz API → Quiz frontend → Database migrations → Email service → Payment integration
- **Phase 2 (AI & Generation)**: AI integration → PDF generation → Authentication → Download system
- **Phase 3 (Operations)**: Manual resolution queue → Admin dashboard → Monitoring/Logging
- **Phase 4 (Optimization)**: Performance testing → Security audit → Pre-launch testing

Context: Spec v1.2.0 already includes hybrid authentication architecture and 18 security patches from previous loophole analysis.

## Response snapshot

Successfully executed complete `/sp.plan` workflow with Plan subagent to generate all Phase 0 and Phase 1 artifacts:

**Constitution Check**: ✅ ALL 10 PRINCIPLES COMPLIANT
- Principle I (Personalization): 20-step quiz structure defined
- Principle II (User Control): Manual edits in future roadmap
- Principle III (Phased Delivery): MVP scope clearly bounded
- Principle IV (No Subscriptions): One-time $9.99 payment
- Principle V (Secure Processing): HMAC webhooks, magic links, rate limiting
- Principle VI (Privacy): 90-day retention, GDPR-compliant deletion
- Principle VII (AI Transparency): Gemini fallback, manual resolution queue
- Principle VIII (Extensibility): Database designed for multi-diet expansion
- Principle IX (Modern Stack): Next.js 16, FastAPI, PostgreSQL, Redis
- Principle X (Accurate Calories): Mifflin-St Jeor formula mandatory

**Technical Context Resolved** (all "NEEDS CLARIFICATION" eliminated):
- **Language/Version**: Next.js 16.1.0 (TypeScript 5+), FastAPI 0.115+ (Python 3.11+)
- **Primary Dependencies**: SQLAlchemy 2.0+, Pydantic 2+, Paddle Billing, OpenAI Agents SDK, Resend, Vercel Blob
- **Storage**: PostgreSQL 15+ (Vercel Postgres), Redis (Upstash), Vercel Blob (PDFs)
- **Testing**: pytest + pytest-asyncio (backend), Vitest + React Testing Library (frontend)
- **Performance Goals**: <90s quiz→email (p95), <20s AI generation (p95), <500ms DB queries (p95)
- **Constraints**: <200ms API latency (p95), <512MB serverless memory, 10-second timeout
- **Scale/Scope**: 10k users/month target, 20-step quiz, 5 PDF deliverables, 4 auth flows

**Project Structure Decision**: Web application (Option 2) with backend + frontend separation

**Artifacts Generated**:

1. **plan.md** - Fully populated implementation plan (no placeholders):
   - Complete technical context
   - Constitution compliance check
   - Project structure with /backend and /frontend directories
   - Complexity tracking table (empty - no violations)

2. **research.md** - Technology research and best practices:
   - 5 technology decisions (PostgreSQL+SQLAlchemy, Next.js 16 App Router, OpenAI Agents SDK with Gemini fallback, Paddle Billing, Resend email)
   - 3 integration patterns (webhook handling with HMAC, email normalization, distributed locks)
   - 3 best practices (async/await, environment config, structured logging)
   - 3 security considerations (OWASP top 10, rate limiting, data retention)
   - Complete code examples for email normalization and Redis locks

3. **data-model.md** - Complete database schema:
   - 6 entities: users, quiz_sessions, purchases, pdfs, email_blacklist, manual_resolution_queue
   - All fields with types, constraints, indexes
   - Relationships and foreign keys
   - State transition diagrams for quiz_sessions (draft→submitted→generating→completed→failed)
   - JSONB schemas for preferences_summary and quiz_responses

4. **contracts/api.yaml** - API contract summary:
   - 15 endpoints across 6 categories
   - Quiz Management: POST/GET/PATCH /api/quiz/sessions
   - Payment: POST /api/payment/initiate, POST /webhooks/paddle
   - Generation: POST /api/generate/meal-plan
   - Authentication: POST /api/auth/send-magic-link, POST /api/auth/verify
   - PDF: GET /api/pdfs/{id}/download
   - Admin: GET /api/admin/manual-queue

5. **quickstart.md** - Complete setup guide:
   - Local development setup (Python venv, npm install, PostgreSQL, Redis)
   - Environment variables for 9 services
   - Database migration commands (alembic)
   - Deployment instructions (Vercel for frontend/backend)

**Key Architectural Decisions Identified** (ADR candidates):
1. Email normalization strategy (Gmail dot/+tag handling)
2. Manual resolution queue workflow (4-hour SLA, automatic refund)
3. Distributed lock implementation (Redis SETNX vs PostgreSQL advisory locks)

## Outcome

- ✅ Impact: Complete planning phase execution - generated 5 implementation artifacts (plan.md, research.md, data-model.md, contracts, quickstart.md) with zero placeholders and full constitution compliance; resolved all technical uncertainties from template
- 🧪 Tests: No tests (planning phase only); artifacts include testing strategy (pytest/Vitest) and test structure (/tests directories)
- 📁 Files: Created plan.md (fully populated), research.md (5 decisions + code samples), data-model.md (6 entities + schemas), contracts/api.yaml (15 endpoints), quickstart.md (setup guide)
- 🔁 Next prompts: 1) Run `/sp.tasks` to break down implementation into dependency-ordered testable tasks, 2) Create ADRs for 3 significant architectural decisions (email normalization, manual queue, distributed locks), 3) Begin Phase 1 implementation (database migrations + quiz API)
- 🧠 Reflection: Plan subagent successfully integrated user-provided milestones with spec v1.2.0 security patches; hybrid auth architecture preserved in all planning artifacts; constitution check passed without violations; Redis dependency introduced for distributed locks (cost tradeoff vs PostgreSQL advisory locks - monitor in production)

## Evaluation notes (flywheel)

- Failure modes observed: None during planning execution; potential risk: Redis cost on free tier may require fallback to PostgreSQL advisory locks if Upstash limits exceeded
- Graders run and results (PASS/FAIL): Constitution compliance check - PASS (10/10 principles met); Technical context completeness - PASS (all NEEDS CLARIFICATION resolved); Artifact generation - PASS (5/5 deliverables created); Placeholder elimination - PASS (0 remaining {{TEMPLATE}} markers)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Monitor Redis distributed lock usage in Phase 1 implementation; if cost prohibitive, experiment with PostgreSQL advisory locks (pg_advisory_xact_lock) as zero-cost alternative while maintaining transaction safety guarantees
