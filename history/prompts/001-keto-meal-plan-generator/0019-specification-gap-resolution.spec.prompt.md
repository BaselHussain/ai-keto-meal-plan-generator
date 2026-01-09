---
id: 0019
title: Specification Gap Resolution
stage: spec
date: 2026-01-01
surface: agent
model: claude-sonnet-4-5
feature: 001-keto-meal-plan-generator
branch: 001-keto-meal-plan-generator
user: developer
command: /sp.clarify
labels: ["specification", "clarification", "gap-resolution", "security", "authentication", "blob-storage", "email-normalization", "payment-flow"]
links:
  spec: specs/001-keto-meal-plan-generator/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-keto-meal-plan-generator/spec.md
tests:
  - None (specification clarification only)
---

## Prompt

User provided context for prioritization: address these gaps

Identified gaps to resolve:
1. Admin Authentication (FR-M-005) - /admin/manual-resolution requires authentication, but no auth mechanism specified
2. Vercel Blob Signed URL Expiry - Spec says 90-day PDF retention, but Vercel Blob signed URLs have their own expiry (typically 7 days or custom). Mismatch: User might not be able to download after URL expires but before 90 days
3. Email Normalization for Non-Gmail Providers - FR-P-010 only covers Gmail/Googlemail (dots, plus-tags). What about Yahoo+, Outlook+, Protonmail aliases? Gap: Potential bypass via other providers
4. Paddle Modal Abandonment - User verifies email → Opens Paddle modal → Closes it without paying. Is the quiz still valid? Does verification expire? Edge case: Quiz might be stuck in limbo
5. Concurrent Payment Race Condition - User opens checkout on 2 devices with same email. Redis lock uses payment_lock:{normalized_email} with 60s TTL. What if: Lock acquired on device A, expires, then device B acquires it?

## Response snapshot

Successfully resolved all 5 specification gaps through targeted clarification questions:

**Q1: Admin Authentication**
- Decision: API key authentication with IP whitelist
- Rationale: Simple to implement, no session management overhead, secure for internal admin tool
- Updated: FR-M-005 with detailed authentication requirements

**Q2: Vercel Blob URL Expiry**
- Decision: Generate fresh signed URLs on-demand (not pre-generated)
- Rationale: Prevents URL expiry mismatch, maintains security, ensures PDF always accessible during 90-day retention
- Updated: FR-D-005, FR-D-006, FR-R-003, FR-E-002 with on-demand generation pattern

**Q3: Email Normalization Scope**
- Decision: Gmail-only normalization (current spec)
- Rationale: Gmail is dominant provider (~30% market share), plus-tag aliasing primarily Gmail feature, diminishing returns vs complexity tradeoff
- Updated: Added clarification confirming current FR-P-010 approach, accepted non-Gmail bypass risk for MVP

**Q4: Paddle Modal Abandonment**
- Decision: Quiz/verification remains valid for 24 hours
- Rationale: Allows users to abandon payment and return later without re-doing quiz, reduces friction for legitimate interrupted users
- Updated: FR-Q-019 with 24-hour verification validity window

**Q5: Concurrent Payment Race Condition**
- Decision: Accept race condition risk as acceptable for MVP
- Rationale: Narrow exploit window (60s), two-layer protection (Redis lock + 10-min DB check), extremely rare in practice, minimal value from additional complexity
- Updated: Added clarification documenting accepted risk with rationale

Spec version updated: 1.2.0 → 1.3.0
All changes documented in Session 2026-01-01 clarifications and Document History

## Outcome

- ✅ Impact: All 5 critical specification gaps resolved; spec now 100% ready for architecture planning phase
- 🧪 Tests: No tests required (specification clarification only)
- 📁 Files: 1 file modified (spec.md) - added 5 clarifications, updated 6 FRs, updated version to 1.3.0
- 🔁 Next prompts: Run /sp.plan to generate implementation plan and architecture decisions
- 🧠 Reflection: Clarification process successfully identified and resolved ambiguities that could have caused implementation delays or rework; on-demand signed URL pattern particularly important for preventing user access issues during 90-day retention period

## Evaluation notes (flywheel)

- Failure modes observed: None - all questions answered clearly, decisions aligned with MVP scope and existing architecture
- Graders run and results (PASS/FAIL): N/A (specification work)
- Prompt variant (if applicable): Standard /sp.clarify workflow with gap-focused prioritization
- Next experiment (smallest change to try): Proceed to /sp.plan phase to validate that clarified requirements translate cleanly into architecture decisions
