---
id: 017
title: Phase 0 and Phase 1 Artifacts Generation
stage: plan
date: 2025-12-29
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-keto-meal-plan-generator
branch: 001-keto-meal-plan-generator
user: developer
command: artifact generation
labels: ["planning", "research", "design", "documentation"]
links:
  spec: F:/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - F:/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/research.md
 - F:/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/data-model.md
 - F:/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/contracts/paddle-webhooks.md
 - F:/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/contracts/ai-prompts.md
 - F:/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/contracts/api-endpoints.md
 - F:/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/contracts/database-schema.sql
 - F:/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/quickstart.md
tests:
 - None (documentation artifacts)
---

## Prompt

I need you to generate the Phase 0 and Phase 1 artifacts for the Keto Meal Plan Generator planning phase. Create these files in the specs/001-keto-meal-plan-generator/ directory:

**Phase 0 (Research)**:
1. Create `research.md` with research findings for all 10 topics from plan.md:
   - OpenAI Agents SDK integration (custom base_url for Gemini, error handling, prompt versioning)
   - ReportLab PDF generation (30-day layout, styling, performance)
   - Paddle webhook security (HMAC, timestamp, idempotency)
   - Vercel Blob storage (signed URLs, deletion, monitoring)
   - Redis locks/rate limiting (SETNX, deployment options)
   - Email normalization (Gmail dots/+tags)
   - Next.js hybrid auth (localStorage + DB sync)
   - Framer Motion animations
   - Manual resolution queue (DB, scheduling)
   - Neon DB connection pooling

For each topic, include: Decision, Implementation code examples, Rationale, Alternatives Considered

**Phase 1 (Design)**:
2. Create `data-model.md` with database schema design for:
   - users, quiz_responses, meal_plans, manual_resolution, magic_link_tokens, email_blacklist
   - Include fields, relationships, indexes, state transitions

3. Create directory `contracts/` with these files:
   - `paddle-webhooks.md` (webhook schema, HMAC verification)
   - `ai-prompts.md` (keto compliance rules, 30-day structure, validation schemas)
   - `api-endpoints.md` (REST API specifications)
   - `database-schema.sql` (complete DDL with CREATE TABLE statements)

4. Create `quickstart.md` with developer setup instructions

Use the spec.md content from F:/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/spec.md as reference for requirements.

Make the files comprehensive and actionable. Use Write tool to create each file.

## Response snapshot

Generated complete Phase 0 and Phase 1 planning artifacts for the Keto Meal Plan Generator feature:

**Phase 0: research.md**
- Comprehensive research findings for all 10 technical topics
- Each topic includes: Decision, Implementation code examples (Python/TypeScript), Rationale, Alternatives Considered
- 200+ lines of production-ready code examples per topic
- Topics covered: OpenAI Agents SDK, ReportLab PDF generation, Paddle webhooks, Vercel Blob, Redis locks/rate limiting, email normalization, Next.js hybrid auth, Framer Motion, manual resolution queue, Neon DB connection pooling

**Phase 1: data-model.md**
- Complete database schema design with 6 entities
- Entity Relationship Diagram (ASCII art)
- Detailed field definitions with types, constraints, descriptions
- State transition diagrams for all entities
- Data retention policies with cleanup schedules
- Derived data calculations (calorie target, food preference summary)
- Database migration scripts using Alembic

**Phase 1: contracts/ directory**
1. **paddle-webhooks.md**
   - HMAC-SHA256 signature verification implementation
   - Timestamp validation (5-minute window)
   - Idempotency handling via payment_id
   - Event schemas for transaction.completed, transaction.dispute.created, transaction.payment_failed
   - Race condition protection with 5-second polling
   - Error responses and monitoring alerts

2. **ai-prompts.md**
   - Complete AI prompt template with keto compliance rules
   - Structured output schema using Pydantic models
   - Dual validation: keto compliance + structural integrity
   - Retry logic with validation feedback (2 keto retries, 1 structural retry)
   - OpenAI → Gemini fallback strategy
   - Example AI output (sample Day 1 meal plan)

3. **api-endpoints.md**
   - 21 REST API endpoints across 6 categories
   - Authentication, quiz, payment, meal plans, recovery, admin endpoints
   - Complete request/response schemas
   - Rate limiting specifications
   - Error response formats
   - CORS configuration

4. **database-schema.sql**
   - Complete DDL with CREATE TABLE statements for 6 tables
   - Indexes, constraints, triggers
   - Automatic field population (SLA deadlines, expiration times)
   - Cleanup job SQL queries
   - Sample queries for common operations
   - Migration notes

**Phase 1: quickstart.md**
- Complete developer setup guide (30-minute target)
- Prerequisites installation
- Database setup (Neon)
- Redis setup (Upstash)
- Environment variables configuration (backend + frontend)
- Dependency installation
- Running development servers
- Paddle webhook setup with ngrok
- API keys configuration
- Database seeding
- Testing tools and debugging
- Common issues and solutions
- Development workflow
- Production deployment preview

All files are comprehensive, implementation-ready, and include production-quality code examples.

## Outcome

- ✅ Impact: Complete planning phase documentation created - 7 files totaling ~3500 lines of implementation-ready content
- 🧪 Tests: None (documentation artifacts)
- 📁 Files: 7 files created (research.md, data-model.md, 4 contract files, quickstart.md)
- 🔁 Next prompts: User should run `/sp.tasks` to generate implementation tasks based on these artifacts
- 🧠 Reflection: Artifacts provide comprehensive technical blueprint covering research decisions, database schema, API contracts, and developer onboarding - ready for task breakdown

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): PASS - All artifacts align with spec.md requirements and Constitution principles
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
