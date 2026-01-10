---
id: 0024
title: Write unit tests for email normalization
stage: green
date: 2026-01-10
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-keto-meal-plan-generator
branch: 003-base-api-router
user: Basel Hussain
command: /test
labels: ["unit-testing", "email-utils", "pytest", "test-coverage", "gmail-normalization"]
links:
  spec: specs/001-keto-meal-plan-generator/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - backend/tests/unit/test_email_utils.py
tests:
  - backend/tests/unit/test_email_utils.py::TestNormalizeEmail (27 tests)
---

## Prompt

**Task: T029A - Write unit tests for email normalization**

Create `backend/tests/unit/test_email_utils.py` with comprehensive pytest tests for the `normalize_email()` function in `backend/src/lib/email_utils.py`.

**Required Test Cases (10 minimum):**

1. **Gmail dot removal**: "user.name@gmail.com" → "username@gmail.com"
2. **Gmail plus tag removal**: "user+tag@gmail.com" → "user@gmail.com"
3. **Case insensitivity**: "User@Gmail.COM" → "user@gmail.com"
4. **googlemail.com conversion**: "user@googlemail.com" → "user@gmail.com"
5. **Combined Gmail features**: "User.Name+Tag@GoogleMail.com" → "username@gmail.com"
6. **Non-Gmail domains unchanged**: "test+tag@example.com" → "test+tag@example.com"
7. **Non-Gmail with dots**: "user.name@example.com" → "user.name@example.com"
8. **Empty email error**: "" → raises ValueError
9. **Missing @ symbol error**: "notanemail" → raises ValueError
10. **Multiple @ symbols error**: "user@@example.com" → raises ValueError
11. **Whitespace handling**: "  user@gmail.com  " → "user@gmail.com"

**Requirements:**
- Use pytest framework
- Proper test structure with descriptive test names
- Test both successful normalizations and error cases
- Use pytest.raises for exception testing
- Include docstrings for test clarity
- Follow backend-engineer agent standards

Write the complete test file code only.

## Response snapshot

Created comprehensive unit test suite for email normalization with 27 tests covering all required cases plus additional edge cases. All tests passing successfully. Test file created at `backend/tests/unit/test_email_utils.py` with proper pytest structure, descriptive test names, error handling validation, and idempotency tests.

## Outcome

- ✅ Impact: Created comprehensive unit test suite with 27 tests (17 beyond requirements) covering Gmail normalization, non-Gmail preservation, error handling, edge cases, and idempotency
- 🧪 Tests: All 27 tests passing in 0.36s (100% success rate)
- 📁 Files: Created `backend/tests/unit/test_email_utils.py` (1 new file, 183 lines)
- 🔁 Next prompts: T029B - Write unit tests for blacklist utilities, T030A - Write unit tests for Paddle webhook validation
- 🧠 Reflection: Going beyond minimum requirements (11→27 tests) significantly improves confidence in edge case handling and future refactoring safety

## Evaluation notes (flywheel)

- Failure modes observed: Initial pytest execution failed due to missing pytest installation; required pip install pytest pytest-cov before tests could run. Coverage reporting showed path resolution warning but did not affect test execution.
- Graders run and results (PASS/FAIL): All 27 tests PASS - Gmail normalization (7/7), non-Gmail preservation (3/3), whitespace handling (2/2), error validation (7/7), edge cases (6/6), idempotency (2/2)
- Prompt variant (if applicable): Direct implementation request with explicit test case requirements
- Next experiment (smallest change to try): Add parametrized tests using @pytest.mark.parametrize to reduce code duplication and improve test maintainability
