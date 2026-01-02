---
id: 0018
title: Add Payment Transactions Table for Analytics and Compliance
stage: spec
date: 2026-01-01
surface: agent
model: claude-sonnet-4-5
feature: 001-keto-meal-plan-generator
branch: 001-keto-meal-plan-generator
user: cw
command: none
labels: ["payment", "database", "analytics", "compliance", "FR-P-013"]
links:
  spec: specs/001-keto-meal-plan-generator/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-keto-meal-plan-generator/spec.md (added FR-P-013)
  - specs/001-keto-meal-plan-generator/data-model.md (added PaymentTransaction entity)
  - specs/001-keto-meal-plan-generator/contracts/payment-webhooks.yaml (updated webhook flows)
  - specs/001-keto-meal-plan-generator/tasks.md (added T016A, T064A-T064C, T116A, T120A, T133A)
  - IMPLEMENTATION-GUIDE.md (updated Phase 2, 3, 10)
tests:
  - No tests added (spec phase only)
---

## Prompt

User asked: "can we add a feature like whenever user buys plan using paddle that payment information is also saved to database? first tell me"

After analyzing the current implementation, I confirmed that only `payment_id` was being saved. The user loved the proposal for a comprehensive `payment_transactions` table and requested updates to all relevant spec files (spec.md, tasks.md, etc.) and IMPLEMENTATION-GUIDE.md.

## Response snapshot

Proposed and implemented comprehensive payment transaction tracking with the following key elements:

**New Table: `payment_transactions`**
- Stores: payment_id, amount, currency, payment_method, payment_status, timestamps
- Purpose: Analytics, customer support, compliance, fraud detection
- Retention: 1 year (aligned with manual_resolution table for audit compliance)
- Security: PCI-DSS compliant (no card numbers, CVV, or sensitive payment data)

**Functional Requirement: FR-P-013**
- Extract payment metadata from Paddle webhooks
- Normalize email per FR-P-010
- Link to meal_plan via FK (nullable initially)
- Update payment_status on refund/chargeback events
- Enable analytics queries without external API calls

**Implementation Tasks Added:**
- T016A: Create PaymentTransaction SQLAlchemy model
- T064A-T064C: Store payment metadata in webhook handler
- T116A: Update status to "chargeback" on chargeback webhook
- T120A: Update status to "refunded" on refund webhook
- T133A: Create cleanup job for 1-year retention

**Benefits:**
1. Revenue tracking by payment method (card vs Apple Pay conversion rates)
2. Customer support (quick payment lookup without Paddle API)
3. Fraud detection (multiple payment patterns, abuse prevention)
4. Compliance (1-year financial records for tax/accounting)

## Outcome

- ✅ Impact: Enhanced payment analytics, faster customer support, compliance readiness, fraud detection capabilities
- 🧪 Tests: No tests added (spec/design phase only - implementation tests will be added during Phase 6-7)
- 📁 Files: Updated 5 spec files (spec.md, data-model.md, payment-webhooks.yaml, tasks.md, IMPLEMENTATION-GUIDE.md)
- 🔁 Next prompts: Implementation tasks T016A, T064A-T064C, T116A, T120A, T133A during respective phases
- 🧠 Reflection: User-driven feature request that significantly improves operational capabilities; demonstrates value of storing safe transaction metadata for business intelligence without PCI-DSS concerns

## Evaluation notes (flywheel)

- Failure modes observed: None - straightforward spec enhancement with clear benefits and no security/compliance risks
- Graders run and results (PASS/FAIL): N/A (spec phase)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): During implementation, measure actual storage overhead and query performance for analytics queries
