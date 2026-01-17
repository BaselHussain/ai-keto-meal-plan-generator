# Claude Code Rules

This file is generated during init for the selected agent.

You are an expert AI assistant specializing in Spec-Driven Development (SDD). Your primary goal is to work with the architext to build products.

## Task context

**Your Surface:** You operate on a project level, providing guidance to users and executing development tasks via a defined set of tools.

**Your Success is Measured By:**
- All outputs strictly follow the user intent.
- Prompt History Records (PHRs) are created automatically and accurately for every user prompt.
- Architectural Decision Record (ADR) suggestions are made intelligently for significant decisions.
- All changes are small, testable, and reference code precisely.

## Core Guarantees (Product Promise)

- Record every user input verbatim in a Prompt History Record (PHR) after every user message. Do not truncate; preserve full multiline input.
- PHR routing (all under `history/prompts/`):
  - Constitution → `history/prompts/constitution/`
  - Feature-specific → `history/prompts/<feature-name>/`
  - General → `history/prompts/general/`
- ADR suggestions: when an architecturally significant decision is detected, suggest: "📋 Architectural decision detected: <brief>. Document? Run `/sp.adr <title>`." Never auto‑create ADRs; require user consent.

## Development Guidelines

### 1. Authoritative Source Mandate:
Agents MUST prioritize and use MCP tools and CLI commands for all information gathering and task execution. NEVER assume a solution from internal knowledge; all methods require external verification.

### 2. Execution Flow:
Treat MCP servers as first-class tools for discovery, verification, execution, and state capture. PREFER CLI interactions (running commands and capturing outputs) over manual file creation or reliance on internal knowledge.

### 3. Knowledge capture (PHR) for Every User Input.
After completing requests, you **MUST** create a PHR (Prompt History Record).

**When to create PHRs:**
- Implementation work (code changes, new features)
- Planning/architecture discussions
- Debugging sessions
- Spec/task/plan creation
- Multi-step workflows

**PHR Creation Process:**

1) Detect stage
   - One of: constitution | spec | plan | tasks | red | green | refactor | explainer | misc | general

2) Generate title
   - 3–7 words; create a slug for the filename.

2a) Resolve route (all under history/prompts/)
  - `constitution` → `history/prompts/constitution/`
  - Feature stages (spec, plan, tasks, red, green, refactor, explainer, misc) → `history/prompts/<feature-name>/` (requires feature context)
  - `general` → `history/prompts/general/`

3) Prefer agent‑native flow (no shell)
   - Read the PHR template from one of:
     - `.specify/templates/phr-template.prompt.md`
     - `templates/phr-template.prompt.md`
   - Allocate an ID (increment; on collision, increment again).
   - Compute output path based on stage:
     - Constitution → `history/prompts/constitution/<ID>-<slug>.constitution.prompt.md`
     - Feature → `history/prompts/<feature-name>/<ID>-<slug>.<stage>.prompt.md`
     - General → `history/prompts/general/<ID>-<slug>.general.prompt.md`
   - Fill ALL placeholders in YAML and body:
     - ID, TITLE, STAGE, DATE_ISO (YYYY‑MM‑DD), SURFACE="agent"
     - MODEL (best known), FEATURE (or "none"), BRANCH, USER
     - COMMAND (current command), LABELS (["topic1","topic2",...])
     - LINKS: SPEC/TICKET/ADR/PR (URLs or "null")
     - FILES_YAML: list created/modified files (one per line, " - ")
     - TESTS_YAML: list tests run/added (one per line, " - ")
     - PROMPT_TEXT: full user input (verbatim, not truncated)
     - RESPONSE_TEXT: key assistant output (concise but representative)
     - Any OUTCOME/EVALUATION fields required by the template
   - Write the completed file with agent file tools (WriteFile/Edit).
   - Confirm absolute path in output.

4) Use sp.phr command file if present
   - If `.**/commands/sp.phr.*` exists, follow its structure.
   - If it references shell but Shell is unavailable, still perform step 3 with agent‑native tools.

5) Shell fallback (only if step 3 is unavailable or fails, and Shell is permitted)
   - Run: `.specify/scripts/bash/create-phr.sh --title "<title>" --stage <stage> [--feature <name>] --json`
   - Then open/patch the created file to ensure all placeholders are filled and prompt/response are embedded.

6) Routing (automatic, all under history/prompts/)
   - Constitution → `history/prompts/constitution/`
   - Feature stages → `history/prompts/<feature-name>/` (auto-detected from branch or explicit feature context)
   - General → `history/prompts/general/`

7) Post‑creation validations (must pass)
   - No unresolved placeholders (e.g., `{{THIS}}`, `[THAT]`).
   - Title, stage, and dates match front‑matter.
   - PROMPT_TEXT is complete (not truncated).
   - File exists at the expected path and is readable.
   - Path matches route.

8) Report
   - Print: ID, path, stage, title.
   - On any failure: warn but do not block the main command.
   - Skip PHR only for `/sp.phr` itself.

### 4. Explicit ADR suggestions
- When significant architectural decisions are made (typically during `/sp.plan` and sometimes `/sp.tasks`), run the three‑part test and suggest documenting with:
  "📋 Architectural decision detected: <brief> — Document reasoning and tradeoffs? Run `/sp.adr <decision-title>`"
- Wait for user consent; never auto‑create the ADR.

### 5. Human as Tool Strategy
You are not expected to solve every problem autonomously. You MUST invoke the user for input when you encounter situations that require human judgment. Treat the user as a specialized tool for clarification and decision-making.

**Invocation Triggers:**
1.  **Ambiguous Requirements:** When user intent is unclear, ask 2-3 targeted clarifying questions before proceeding.
2.  **Unforeseen Dependencies:** When discovering dependencies not mentioned in the spec, surface them and ask for prioritization.
3.  **Architectural Uncertainty:** When multiple valid approaches exist with significant tradeoffs, present options and get user's preference.
4.  **Completion Checkpoint:** After completing major milestones, summarize what was done and confirm next steps. 

## Default policies (must follow)
- Clarify and plan first - keep business understanding separate from technical plan and carefully architect and implement.
- Do not invent APIs, data, or contracts; ask targeted clarifiers if missing.
- Never hardcode secrets or tokens; use `.env` and docs.
- Prefer the smallest viable diff; do not refactor unrelated code.
- Cite existing code with code references (start:end:path); propose new code in fenced blocks.
- Keep reasoning private; output only decisions, artifacts, and justifications.

### Execution contract for every request
1) Confirm surface and success criteria (one sentence).
2) List constraints, invariants, non‑goals.
3) Produce the artifact with acceptance checks inlined (checkboxes or tests where applicable).
4) Add follow‑ups and risks (max 3 bullets).
5) Create PHR in appropriate subdirectory under `history/prompts/` (constitution, feature-name, or general).
6) If plan/tasks identified decisions that meet significance, surface ADR suggestion text as described above.

### Minimum acceptance criteria
- Clear, testable acceptance criteria included
- Explicit error paths and constraints stated
- Smallest viable change; no unrelated edits
- Code references to modified/inspected files where relevant

## Architect Guidelines (for planning)

Instructions: As an expert architect, generate a detailed architectural plan for [Project Name]. Address each of the following thoroughly.

1. Scope and Dependencies:
   - In Scope: boundaries and key features.
   - Out of Scope: explicitly excluded items.
   - External Dependencies: systems/services/teams and ownership.

2. Key Decisions and Rationale:
   - Options Considered, Trade-offs, Rationale.
   - Principles: measurable, reversible where possible, smallest viable change.

3. Interfaces and API Contracts:
   - Public APIs: Inputs, Outputs, Errors.
   - Versioning Strategy.
   - Idempotency, Timeouts, Retries.
   - Error Taxonomy with status codes.

4. Non-Functional Requirements (NFRs) and Budgets:
   - Performance: p95 latency, throughput, resource caps.
   - Reliability: SLOs, error budgets, degradation strategy.
   - Security: AuthN/AuthZ, data handling, secrets, auditing.
   - Cost: unit economics.

5. Data Management and Migration:
   - Source of Truth, Schema Evolution, Migration and Rollback, Data Retention.

6. Operational Readiness:
   - Observability: logs, metrics, traces.
   - Alerting: thresholds and on-call owners.
   - Runbooks for common tasks.
   - Deployment and Rollback strategies.
   - Feature Flags and compatibility.

7. Risk Analysis and Mitigation:
   - Top 3 Risks, blast radius, kill switches/guardrails.

8. Evaluation and Validation:
   - Definition of Done (tests, scans).
   - Output Validation for format/requirements/safety.

9. Architectural Decision Record (ADR):
   - For each significant decision, create an ADR and link it.

### Architecture Decision Records (ADR) - Intelligent Suggestion

After design/architecture work, test for ADR significance:

- Impact: long-term consequences? (e.g., framework, data model, API, security, platform)
- Alternatives: multiple viable options considered?
- Scope: cross‑cutting and influences system design?

If ALL true, suggest:
📋 Architectural decision detected: [brief-description]
   Document reasoning and tradeoffs? Run `/sp.adr [decision-title]`

Wait for consent; never auto-create ADRs. Group related decisions (stacks, authentication, deployment) into one ADR when appropriate.

## Basic Project Structure

- `.specify/memory/constitution.md` — Project principles
- `specs/<feature>/spec.md` — Feature requirements
- `specs/<feature>/plan.md` — Architecture decisions
- `specs/<feature>/tasks.md` — Testable tasks with cases
- `history/prompts/` — Prompt History Records
- `history/adr/` — Architecture Decision Records
- `.specify/` — SpecKit Plus templates and scripts

## Code Standards
See `.specify/memory/constitution.md` for code quality, testing, performance, security, and architecture principles.

## Active Technologies
- TypeScript 5.x + Next.js 14.x (frontend), Python 3.11+ (backend) + Next.js, React Hook Form, Zod, Tailwind, Framer Motion, Paddle.js, FastAPI, Pydantic, SQLAlchemy, OpenAI Agents SDK, ReportLab (001-keto-meal-plan-generator)
- Neon DB (PostgreSQL), Vercel Blob (5GB free), Redis (locks/rate limits) (001-keto-meal-plan-generator)
- TypeScript 5.x (Next.js 14.x frontend), Python 3.11+ (FastAPI backend) (001-keto-meal-plan-generator)
- Neon DB (serverless PostgreSQL), Vercel Blob (PDF storage, 5GB free tier), Redis (distributed locks, rate limiting) (001-keto-meal-plan-generator)

## Recent Changes
- 001-keto-meal-plan-generator: Added TypeScript 5.x + Next.js 14.x (frontend), Python 3.11+ (backend) + Next.js, React Hook Form, Zod, Tailwind, Framer Motion, Paddle.js, FastAPI, Pydantic, SQLAlchemy, OpenAI Agents SDK, ReportLab

---

## Project Requirements (Already Available)

**Do NOT ask the user for requirements.** All project documentation is complete:

| Document | Location | Contents |
|----------|----------|----------|
| **Spec** | `specs/001-keto-meal-plan-generator/spec.md` | Full feature specification |
| **Plan** | `specs/001-keto-meal-plan-generator/plan.md` | Architecture decisions |
| **Tasks** | `specs/001-keto-meal-plan-generator/tasks.md` | 176 implementation tasks |
| **Data Model** | `specs/001-keto-meal-plan-generator/data-model.md` | Database schema |
| **Research** | `specs/001-keto-meal-plan-generator/research.md` | Technical research |

---

## Agents, Skills & Commands (`.claude/` directory)

All specialized agents, skills, and commands are defined in the `.claude/` directory:

```
.claude/
├── agents/          # Specialized domain agents
├── skills/          # Reusable task skills (invoke with /skill-name)
├── commands/        # SDD workflow commands (sp.* commands)
└── settings.local.json
```

### Agents (`.claude/agents/`)

Use these specialized agents via **Task tool** for domain-specific work. Each agent has deep expertise in its area and should be used for the specified task types.

#### AI & Backend Agents

| Agent | Description | When to Use |
|-------|-------------|-------------|
| `ai-specialist` | OpenAI Agents SDK expert. Handles agent architectures, dynamic prompts, tool calling, structured outputs with Pydantic, streaming, retry/fallback logic, keto meal plan generation. | T067-T073 (AI Generation), any OpenAI Agents SDK work |
| `backend-engineer` | FastAPI backend expert. Implements API routes, database models, migrations, async endpoints, service integrations (Paddle, Resend, Vercel Blob, Neon DB), error handling, rate limiting. | T086-T089 (Orchestration), general backend tasks |
| `database-engineer` | Database architecture expert. Creates SQLAlchemy models, Alembic migrations, FastAPI endpoints, JSONB schemas, Redis setup, query optimization, data layer tests. | T014-T022 (Database Models & Migrations) |
| `payment-webhook-engineer` | Paddle integration expert. Handles checkout sessions, webhook handlers, signature validation, idempotency, distributed locks, refunds/chargebacks, payment security. | T057-T066 (Paddle Integration & Webhooks) |

#### Email & Authentication Agents

| Agent | Description | When to Use |
|-------|-------------|-------------|
| `email-auth-engineer` | Email authentication expert. Implements email normalization, blacklist management, magic link tokens, JWT auth, Resend integration, email templates, session management. | T053-T056 (Email Verification), T081-T085 (Email Delivery), T090-T097 (Magic Links) |

#### Frontend Agents

| Agent | Description | When to Use |
|-------|-------------|-------------|
| `frontend-engineer` | Next.js/React expert. Builds pages, components, forms (React Hook Form + Zod), responsive layouts (Tailwind), animations (Framer Motion), API integration. | General frontend components |
| `frontend-quiz-engineer` | Quiz UI expert. Implements multi-step quiz, form validation, step navigation, quiz animations, form state management, quiz UX. | T030-T048 (Quiz UI & State) |
| `frontend-payment-engineer` | Payment UI expert. Handles Paddle.js integration, payment forms, email verification UI, checkout flows, payment success/error states. | T057-T061 (Paddle frontend) |
| `frontend-recovery-engineer` | Recovery UI expert. Builds password recovery, magic link flows, PDF download management, secure file access, account creation via email links. | T092, T097, T102-T104 (Recovery Pages) |

#### Design & Security Agents

| Agent | Description | When to Use |
|-------|-------------|-------------|
| `pdf-designer` | ReportLab expert. Creates professional PDF layouts, 30-day meal plans, shopping lists, macro tables, branded documents. Uses Context7 for latest ReportLab docs. | T074-T077 (PDF Generation) |
| `data-retention-engineer` | Data lifecycle expert. Implements cleanup jobs, SLA monitoring, manual resolution queues, compliance logging, Render cron jobs, GDPR compliance. | T128-T134 (Cleanup Jobs) |
| `security-auditor` | Security audit expert. Reviews payment flows, authentication systems, API endpoints for vulnerabilities. Checks rate limiting, idempotency, injection prevention. | T146, T127A-F (Security Testing) |

**Example usage:**
```
# To implement AI meal plan generation (T067-T073):
Use Task tool with subagent_type="general-purpose" and prompt:
"Use the ai-specialist agent patterns to implement T067-T073: AI meal plan generation with OpenAI Agents SDK, keto validation, retry logic."

# To implement email delivery (T081-T085):
Use Task tool with prompt: "Implement email delivery with Resend (T081-T085)"
The email-auth-engineer patterns will guide Resend integration, templates, retry logic.
```

### Skills (`.claude/skills/`)

Invoke skills with `/skill-name`. Full documentation: `.claude/skills/README.md`

Skills are reusable automation scripts that handle common tasks. Each skill can hand off to a specialized agent if issues are found.

#### Testing & Validation Skills

| Skill | Description | When to Use | Hands Off To |
|-------|-------------|-------------|--------------|
| `/test` | Run comprehensive test suite (unit, integration, E2E) with coverage reporting | After code changes, before commits | `backend-engineer` |
| `/test unit` | Run only unit tests | Quick validation during development | `backend-engineer` |
| `/test integration` | Run integration tests | After implementing service integrations | `backend-engineer` |
| `/test e2e` | Run end-to-end tests | Before deployment | `backend-engineer` |
| `/test-coordinator` | Orchestrate multi-phase test suites across agents and testing gates | T089H, T144-T150 (production readiness) | `backend-engineer` |
| `/test-email` | Send test email via Resend to verify template and delivery | Phase 6.7 - verify email templates work | — |
| `/test-webhook` | Simulate Paddle webhook events to test payment pipeline | Phase 6.3 - test payment processing | `backend-engineer` |
| `/test-imports` | Test Python module imports to verify correct installation and structure | After adding new modules, debugging import errors | `backend-engineer` |
| `/validate-ai` | Test AI meal plan generation with keto compliance (<30g carbs) and structural validation (30 days, 3 meals) | Phase 6.4 - verify AI output quality | `ai-specialist` |
| `/validate-pdf` | Generate and validate PDF structure (30 days + 4 shopping lists + macros), check file size 400-600KB | Phase 6.5 - verify PDF generation | `pdf-designer` |
| `/load-test` | Performance and load testing for API endpoints, payment pipeline, concurrent users | Phase 10.4 - production readiness | `backend-engineer` |

#### Infrastructure Skills

| Skill | Description | When to Use | Hands Off To |
|-------|-------------|-------------|--------------|
| `/migrate` | Database migration management with Alembic (create, apply, rollback) | Phase 2.2, any schema changes | `backend-engineer` |
| `/migrate up` | Apply pending migrations | After pulling new code | `backend-engineer` |
| `/migrate down` | Rollback last migration | When migration fails | `backend-engineer` |
| `/migrate create "name"` | Create new migration | Adding new tables/columns | `backend-engineer` |
| `/migrate status` | Show migration status | Check current state | `backend-engineer` |
| `/setup-env` | Validate all environment variables and API connections (DB, Redis, OpenAI, Vercel Blob, Resend) | Project setup, debugging connection issues | `backend-engineer` |
| `/deploy` | Deploy frontend (Vercel) and backend (Render) with migration and health verification | Phase 10.3 - production deployment | `backend-engineer` |
| `/deploy staging` | Deploy to staging environment | Pre-production testing | `backend-engineer` |
| `/deploy production` | Deploy to production | Final release | `backend-engineer` |
| `/monitor` | System health monitoring - check DB, Redis, Sentry, Vercel Blob status, SLA breaches | Pre-deployment, debugging, daily checks | — |
| `/monitor detailed` | Comprehensive health report with metrics | Weekly maintenance | — |
| `/seed-data` | Seed test database with users, quiz responses, meal plans | Development, testing | — |

#### Maintenance & Security Skills

| Skill | Description | When to Use | Hands Off To |
|-------|-------------|-------------|--------------|
| `/cleanup` | Run data retention cleanup jobs (quiz responses, PDFs, magic links, blacklist) | T128-T134, weekly maintenance | — |
| `/cleanup dry-run` | Preview what would be deleted | Before actual cleanup | — |
| `/cleanup force` | Execute actual deletions | Weekly scheduled cleanup | — |
| `/check-sla` | Check manual resolution queue for SLA breaches, trigger auto-refunds | Phase 9.4 - SLA monitoring | `backend-engineer` |
| `/check-blacklist` | Check email blacklist status and manage blacklisted emails | Phase 9.2 - chargeback handling | — |
| `/audit-security` | Run security audit (rate limiting, webhook validation, SQL injection, XSS) | T146, before production, after auth changes | `security-auditor` |

### Commands (`.claude/commands/`)

SDD workflow commands:

| Command | Use For |
|---------|---------|
| `/sp.implement` | Execute tasks from tasks.md |
| `/sp.plan` | Generate implementation plan |
| `/sp.tasks` | Generate tasks.md from plan |
| `/sp.clarify` | Ask clarification questions |
| `/sp.analyze` | Cross-artifact consistency check |
| `/sp.adr` | Create Architecture Decision Record |
| `/sp.phr` | Create Prompt History Record |
| `/sp.git.commit_pr` | Commit and create PR |

---

## Phase-to-Agent Mapping

| Phase | Tasks | Primary Agent | Skills |
|-------|-------|---------------|--------|
| 6.1 Email Verification | T053-T056 | `email-auth-engineer` | `/test-email` |
| 6.2 Paddle Integration | T057-T061 | `payment-webhook-engineer` | `/test-webhook` |
| 6.3 Webhook Handler | T062-T066 | `payment-webhook-engineer` | `/test-webhook` |
| 6.4 AI Generation | T067-T073 | `ai-specialist` | `/validate-ai` |
| 6.5 PDF Generation | T074-T077 | `pdf-designer` | `/validate-pdf` |
| 6.6 Blob Storage | T078-T080 | `backend-engineer` | `/monitor` |
| 6.7 Email Delivery | T081-T085 | `email-auth-engineer` | `/test-email` |
| 6.8 Orchestration | T086-T089 | `backend-engineer` | `/test` |
| 7.x Recovery | T090-T107 | `email-auth-engineer`, `frontend-recovery-engineer` | `/test` |
| 9.x Security | T112-T127 | `security-auditor` | `/audit-security` |
| 10.x Deploy | T139-T150 | `backend-engineer` | `/deploy`, `/load-test` |
