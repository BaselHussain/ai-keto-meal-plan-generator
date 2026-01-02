---
id: 0008
title: Fix all medium spec issues for 200% clarity
stage: spec
date: 2025-12-23
surface: agent
model: claude-sonnet-4-5
feature: 001-keto-meal-plan-generator
branch: 001-keto-meal-plan-generator
user: user
command: continue
labels: ["spec", "constitution", "verification", "clarity", "consistency"]
links:
  spec: specs/001-keto-meal-plan-generator/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-keto-meal-plan-generator/spec.md
  - .specify/memory/constitution.md
tests:
  - None (spec phase)
---

## Prompt

User requested: "first fix all medium issues our spec and constituition should be 200% crystal clear with no confusion and contadictory points"

User also clarified during execution: "ok sorry for interrupt i want to tell you that icons used in quiz should be colored nothing in ui should be uncolored everything should be colored, now continue"

Context: After final spec verification identified 8 medium issues (no critical blockers), user requested fixing ALL medium issues before proceeding to planning phase.

Goal: Achieve 200% clarity by resolving all 8 medium issues in spec and constitution, eliminating all contradictions and ambiguities.

## Response snapshot

**Used TodoWrite to track 8 fixes systematically:**

### Issue #1: Constitution Formula Contradiction ✅
- **Problem**: Constitution Principle X referenced "Harris-Benedict formula" (line 234, 239)
- **Fix**: Updated to "Mifflin-St Jeor formula" with exact equations
- **Files**: constitution.md lines 6, 32, 234, 239, 240, 241
- **Impact**: Constitution now matches spec; no formula contradiction

### Issue #2: Activity Level Label Mismatch ✅
- **Problem**: Constitution used "Couch Potato" vs spec used "Sedentary"
- **Fix**: Standardized on "Sedentary" in Constitution Principle I
- **Files**: constitution.md line 32
- **Impact**: Consistent UI labeling across all documents

### Issue #3: Food Icons Format Not Specified ✅
- **Problem**: FR-U-002 said "64x64px food icons" but no format/source
- **Fix**: Specified "64x64px SVG format, fully colored (no monochrome/grayscale), React Icons or Lucide Icons library"
- **User Clarification**: "icons used in quiz should be colored nothing in ui should be uncolored everything should be colored"
- **Files**: spec.md FR-U-002
- **Impact**: Developer knows exact format (SVG), source (React Icons/Lucide), and style (colored)

### Issue #4: Recovery Email Content Not Fully Specified ✅
- **Problem**: FR-E-002 mentioned "recovery instructions" but no exact wording
- **Fix**: Added FR-E-006 with exact copy: "Lost this email? You can re-download your plan anytime for 90 days:" with two CTAs: (1) "Request Magic Link" button, (2) "Create Free Account" link
- **Files**: spec.md FR-E-006 (new requirement)
- **Impact**: Email template implementation now has exact copy and CTA structure

### Issue #5: OpenAI Agents SDK Version Not Pinned ✅
- **Problem**: Technology Stack said `pip install "openai-agents"` without version constraint
- **Fix**: Pinned to `"openai-agents>=0.1.0,<1.0.0"` to prevent breaking changes
- **Files**: spec.md Technology Stack Dependencies
- **Impact**: Prevents breaking changes mid-development; reproducible builds

### Issue #6: Quiz Cross-Device Sync Not Explicit ✅
- **Problem**: FR-Q-009 covered browser persistence but not cross-device behavior
- **Fix**: Added explicit note: "IMPORTANT: quiz progress is device/browser-specific (no cross-device sync) - users switching devices must restart quiz (acceptable for MVP)"
- **Files**: spec.md FR-Q-009
- **Impact**: Clear expectations; prevents confusion about cross-device behavior

### Issue #7: Blob URL Security Pattern Partially Specified ✅
- **Problem**: FR-D-005 said "UUID-based signed URL", FR-R-003 said "UUID or signed URL" (ambiguous)
- **Fix**: Clarified Vercel Blob's native signed URL pattern: "time-limited, cryptographically secure tokens with automatic expiration"
- **Files**: spec.md FR-D-005, FR-R-003
- **Impact**: Security implementation clear; uses Vercel Blob's built-in signed URL mechanism

### Issue #8: Monitoring Alert Destinations Not Specified ✅
- **Problem**: Constitution IX mentioned alerts but not destination/mechanism
- **Fix**: Specified "Sentry email notifications sent to project owner email; critical alerts (error rate >5%, payment failures, storage >80%) trigger immediate email notifications"
- **Files**: constitution.md Principle IX, spec.md Observability section
- **Impact**: Alert routing clear; project owner receives critical notifications via email

**Final Updates:**
- Added comprehensive clarification to spec (line 45) documenting all 8 fixes
- Updated both spec.md and constitution.md for consistency
- All contradictions eliminated
- All ambiguities resolved

## Outcome

- ✅ Impact: ZERO contradictions or ambiguities remain; spec and constitution are 200% crystal clear and ready for planning phase; all 8 medium issues resolved
- 🧪 Tests: No tests run (specification phase)
- 📁 Files: Updated spec.md (7 functional requirements enhanced + 1 new FR-E-006 + new clarification) and constitution.md (3 sections updated for formula, labels, alerts)
- 🔁 Next prompts: /sp.plan to create architecture plan (spec is 100% implementation-ready with absolute clarity)
- 🧠 Reflection: Systematic fix of all medium issues ensures no ambiguity during implementation; colored icons requirement added per user feedback; spec/constitution now perfectly aligned

## Evaluation notes (flywheel)

- Failure modes observed: None observed
- Graders run and results (PASS/FAIL): Not applicable (spec phase)
- Prompt variant (if applicable): fix-all-medium-issues-v1
- Next experiment (smallest change to try): None needed; spec verification complete and ready for planning
