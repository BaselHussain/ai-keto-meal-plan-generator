# Project Skills

Reusable skills for the Keto Meal Plan Generator project. These skills streamline common development, testing, and operations tasks.

## 📋 Available Skills

### 🧪 Testing & Validation (Tier 1 - Use Daily)

#### `/test`
Run comprehensive test suite (unit, integration, E2E) with coverage reporting.

```bash
/test              # Run all tests
/test unit         # Run only unit tests
/test integration  # Run integration tests
/test e2e          # Run E2E tests
/test security     # Run security tests
```

**Output**: Test results, coverage report, failing tests with errors

---

#### `/test-coordinator`
Orchestrate multi-phase integration and E2E test suites across multiple agents and testing gates.

```bash
/test-coordinator full-pipeline  # Run T089H (pipeline orchestration)
/test-coordinator ai-quality     # Run T107A-T107F (AI quality validation)
/test-coordinator production     # Run T144-T150 (production readiness)
/test-coordinator phase-6        # Run all Phase 6 integration tests
/test-coordinator phase-7        # Run all Phase 7 AI/PDF/payment tests
/test-coordinator phase-10       # Run all Phase 10 production tests
/test-coordinator all            # Run all test suites sequentially
```

**Output**: Comprehensive test report with results, performance metrics, coverage, failures, recommendations, gate status (PASS/FAIL)

---

#### `/load-test`
Performance and load testing for API endpoints, payment pipeline, and concurrent user scenarios.

```bash
/load-test                    # Test API endpoints (default)
/load-test api-endpoints      # Test API latency
/load-test payment-pipeline   # Test full payment → AI → PDF → email flow
/load-test concurrent-users   # Simulate 50 concurrent quiz submissions
/load-test full-system        # Test all endpoints under load
/load-test all                # Run all load test scenarios
```

**Output**: Performance metrics (p50/p95/p99 latency), bottlenecks, throughput, error rates, recommendations

**Targets**: API <500ms (p95), Full pipeline <90s (p95), 50+ concurrent users, 95%+ success rate

---

#### `/validate-ai`
Test AI meal plan generation with keto compliance and structural validation.

```bash
/validate-ai                # Default weight-loss profile
/validate-ai weight-loss    # Female, sedentary, weight loss
/validate-ai muscle-gain    # Male, very active, muscle gain
/validate-ai maintenance    # Female, moderate, maintenance
```

**Output**: Keto compliance check (<30g carbs), structural validation (30 days, 3 meals, 4 shopping lists), quality score (X/10)

---

#### `/validate-pdf`
Generate and validate PDF structure (30 days + shopping lists + macros).

```bash
/validate-pdf                                        # Use default test fixture
/validate-pdf tests/fixtures/test_meal_plan_muscle_gain.json
```

**Output**: PDF generated, file size check (400-600KB), structure validation, opens PDF for visual review

---

### 🗄️ Database & Infrastructure (Tier 1 - Essential)

#### `/migrate`
Database migration management (create, apply, rollback using Alembic).

```bash
/migrate                          # Apply all pending migrations
/migrate up                       # Apply migrations
/migrate down                     # Rollback last migration
/migrate down 2                   # Rollback 2 migrations
/migrate create "Add user prefs"  # Create new migration
/migrate status                   # Show migration status
/migrate history                  # Show migration history
```

**Output**: Migration status, current version, applied migrations

---

#### `/setup-env`
Environment setup and validation - verify all required environment variables and API connections.

```bash
/setup-env               # Validate all env vars and connections
/setup-env check         # Same as above
/setup-env create        # Create .env files from .env.example
```

**Output**: Environment variable status, API connection tests (DB, Redis, OpenAI, Vercel Blob, Resend), missing variables list

---

### 🚀 Deployment & Operations (Tier 2 - Weekly)

#### `/deploy`
Deploy frontend (Vercel) and backend (Render) with migration and health verification.

```bash
/deploy                  # Deploy to staging
/deploy staging          # Deploy to staging
/deploy production       # Deploy to production
/deploy preview          # Create preview deployment
```

**Output**: Deployment URLs, migration status, health checks, post-deployment checklist

---

#### `/monitor`
System health monitoring - check DB, Redis, Sentry, Vercel Blob, and SLA status.

```bash
/monitor           # Quick status check
/monitor detailed  # Comprehensive report with metrics
```

**Output**: Service status (DB, Redis, Blob, Sentry), storage usage (Blob %, approaching 80%), recent errors, SLA breaches

---

#### `/cleanup`
Run data retention cleanup jobs (quiz responses, PDFs, magic links, blacklist).

```bash
/cleanup              # Dry run - preview deletions
/cleanup dry-run      # Same as above
/cleanup force        # Execute actual deletions
```

**Output**: Deletion counts by type, space reclaimed, audit trail

---

#### `/check-sla`
Check manual resolution queue for SLA breaches and trigger auto-refunds.

```bash
/check-sla         # Report SLA status only
/check-sla alert   # Report + trigger auto-refunds
```

**Output**: SLA breach count, approaching deadlines, auto-refund status, manual queue size

---

### 🔧 Development Utilities (Tier 3 - As Needed)

#### `/test-webhook`
Simulate Paddle webhook events to test payment processing pipeline.

```bash
/test-webhook                     # Test payment success flow
/test-webhook payment-success     # Same as above
/test-webhook chargeback          # Test chargeback handling
/test-webhook refund              # Test refund processing
/test-webhook pay_custom_123      # Use custom payment_id
```

**Includes helper script**: `test_webhook_helper.py` with edge case testing (missing quiz, duplicate, invalid signature, expired timestamp)

**Output**: Webhook processing status, pipeline execution times (AI, PDF, Blob, Email), database verification

---

#### `/seed-data`
Seed test database with users, quiz responses, and meal plans for development.

```bash
/seed-data                # Basic test data (5 users, 10 quizzes, 3 plans)
/seed-data refund-abuse   # Test refund abuse detection (3 refunds in 90d)
/seed-data sla-breach     # Test SLA monitoring (entry past deadline)
```

**Output**: Created records count, test credentials, payment IDs

---

#### `/test-email`
Send test email via Resend to verify template and delivery.

```bash
/test-email                      # Send to test@resend.dev
/test-email user@example.com     # Send to specific address
```

**Output**: Email sent confirmation, message ID, delivery status, template preview

---

### 🔒 Security & Compliance (Tier 3 - Periodic)

#### `/audit-security`
Run security audit checks (rate limiting, webhook validation, SQL injection, XSS).

```bash
/audit-security    # Run all security checks
```

**Output**: Rate limit tests (email, download, recovery, magic link), webhook signature validation, injection protection tests, secrets scan

---

#### `/check-blacklist`
Check email blacklist status and manage blacklisted emails.

```bash
/check-blacklist user@example.com    # Check specific email
/check-blacklist list                # List all blacklisted emails
```

**Output**: Blacklist status, reason (chargeback), expiry date, days remaining

---

## 🎯 Recommended Usage Pattern

### Daily Development
```bash
/setup-env               # Verify environment on startup
/test unit               # Run unit tests after code changes
/validate-ai             # Test AI generation quality
/test-webhook            # Test payment pipeline integration
```

### Before Committing
```bash
/test                    # Run full test suite
/audit-security          # Run security checks
```

### Deployment
```bash
/test                    # Ensure all tests pass
/migrate status          # Check pending migrations
/deploy staging          # Deploy to staging
/monitor                 # Verify health
/deploy production       # Deploy to production
```

### Weekly Maintenance
```bash
/monitor detailed        # Check system health
/check-sla              # Review SLA status
/cleanup dry-run        # Preview data cleanup
/cleanup force          # Execute cleanup
```

---

## 📁 Directory Structure

```
.claude/skills/
├── test/
│   └── SKILL.md
├── test-coordinator/
│   └── SKILL.md
├── load-test/
│   └── SKILL.md
├── migrate/
│   └── SKILL.md
├── setup-env/
│   └── SKILL.md
├── validate-ai/
│   └── SKILL.md
├── validate-pdf/
│   └── SKILL.md
├── test-webhook/
│   ├── SKILL.md
│   └── test_webhook_helper.py    # Python helper script
├── deploy/
│   └── SKILL.md
├── monitor/
│   └── SKILL.md
├── cleanup/
│   └── SKILL.md
├── check-sla/
│   └── SKILL.md
├── seed-data/
│   └── SKILL.md
├── test-email/
│   └── SKILL.md
├── audit-security/
│   └── SKILL.md
└── check-blacklist/
    └── SKILL.md
```

---

## 🔨 Creating New Skills

To create a new skill:

1. Create directory: `.claude/skills/[skill-name]/`
2. Add `SKILL.md` with frontmatter:
   ```yaml
   ---
   description: Brief description of what the skill does
   handoffs:
     - label: Follow-up Action
       agent: backend-engineer
       prompt: What to do next
       send: false
   ---
   ```
3. Define steps and examples
4. Add helper scripts if needed (Python, Bash)
5. Document in this README

---

## 📚 Related Documentation

- **Tasks**: See `specs/001-keto-meal-plan-generator/tasks.md` for implementation tasks
- **Spec**: See `specs/001-keto-meal-plan-generator/spec.md` for requirements
- **Quickstart**: See `specs/001-keto-meal-plan-generator/quickstart.md` for setup
- **Constitution**: See `.specify/memory/constitution.md` for project principles

---

**Total Skills**: 16 (7 Tier 1, 4 Tier 2, 5 Tier 3)
**Last Updated**: 2026-01-02
