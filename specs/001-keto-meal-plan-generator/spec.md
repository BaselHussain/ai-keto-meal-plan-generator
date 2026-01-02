# AI-Powered Personalized Keto Meal Plan Generator Specification

**Feature Branch**: `001-keto-meal-plan-generator`
**Created**: 2025-12-22
**Updated**: 2026-01-01 (Specification Gap Resolution)
**Status**: Active
**Version**: 1.3.0

---

## Overview

The AI-Powered Personalized Keto Meal Plan Generator is a full-stack SaaS application that guides users through a comprehensive 20-step quiz to collect personalized health data, food preferences, and behavioral patterns, then automatically generates a customized 30-day keto meal plan delivered via PDF email within 90 seconds. The product combines modern AI (Gemini/OpenAI), secure payments (Paddle), and production-grade automation to deliver a seamless, privacy-first user experience.

---

## Clarifications

### Session 2025-12-22

- Q: When should user accounts be created in the flow? → A: Accounts optional post-purchase (user receives PDF via email, can optionally create account later for dashboard access)
- Q: What should users see immediately after completing the quiz (step 20)? → A: Review screen showing quiz summary + calorie target, then "Proceed to Payment" button
- Q: Can users request meal plan regeneration after successful delivery? → A: No regeneration in MVP (one-time generation, users accept AI output, defer customization to post-MVP)
### Session 2025-12-23
- Q: What data retention policy should govern quiz responses and meal plan metadata after successful PDF delivery? → A: Delete quiz responses after 24 hours; retain meal plan metadata (PDF URL, calorie target, generation date, payment ID) for 90 days
- Q: What should be the AI provider selection and fallback strategy? → A: Use Gemini for dev/testing, OpenAI for production, with automatic fallback to Gemini if OpenAI fails (3 retries each provider)
- Q: What meal structure should each day in the 30-day plan follow? → A: 3 meals per day (breakfast, lunch, dinner); standard structure that suits most users and simplifies macro distribution
- Q: How should the shopping list in the PDF be structured and scoped? → A: 4 weekly shopping lists (Week 1-4), each organized by ingredient category with quantities; practical for regular shopping trips
- Q: When and how should optional account creation be offered to users after purchase? → A: Optional prompt on success page after PDF email sent ("Create account to access dashboard?" with Skip option); include account creation link in delivery email
- Q: Which BMR calculation formula should the system use? → A: Mifflin-St Jeor (1990): BMR = (10 × weight_kg) + (6.25 × height_cm) - (5 × age) + 5 for men, -161 for women; more accurate for modern populations
- Q: What OpenAI error conditions should trigger immediate fallback to Gemini versus retry with exponential backoff? → A: Immediate fallback on: auth errors, quota exceeded, invalid API key; Retry with backoff on: timeouts (>20s), rate limits (429), server errors (500-503)
- Q: Should the system retain a summary of user food preferences after quiz response deletion? → A: Retain preference summary only (excluded foods list, preferred proteins, dietary restrictions text); helps support without storing biometrics
- Q: How should Paddle webhook signatures be verified and what should happen on verification failure? → A: Verify HMAC-SHA256 signature using Paddle webhook secret from environment variable; log failure + return 401 without processing; alert on repeated failures
- Q: Should quiz data be persisted to the database incrementally as the user progresses through the quiz? → A: Browser-only (localStorage + React state); only save to database on final submission before payment; simpler, more private, no cleanup needed
- Q: How should the system select a specific calorie deficit/surplus value within the stated ranges? → A: Fixed mid-range values: Weight Loss = -400 kcal, Muscle Gain = +250 kcal, Maintenance = 0
- Q: Should the validation checklist reference be corrected from Harris-Benedict to Mifflin-St Jeor for consistency? → A: Yes - Update validation checklist to reference Mifflin-St Jeor formula consistently
- Q: What are the minimum and maximum reasonable height values for validation? → A: Metric: 122-229 cm, Imperial: 4'0"-7'6" (48-90 inches); inclusive range covering 99.9% of adults
- Q: Which PDF generation library should be used for the meal plan PDFs? → A: ReportLab - Industry standard for programmatic PDF generation with precise layout control, better performance, supports beautiful formatting with tables and structured content
- Q: Which blob storage provider should be used for PDF storage? → A: Vercel Blob - Seamless integration with Vercel hosting, simpler auth, 5GB free tier sufficient for MVP; can migrate to Cloudinary later if storage needs grow
- Q: What are the exact activity multipliers for all 5 activity levels? → A: Sedentary: 1.2, Lightly Active: 1.375, Moderately Active: 1.55, Very Active: 1.725, Super Active: 1.9 (standard validated multipliers)
- Q: What are the exact goal selection options the user can choose from at Step 20? → A: Weight Loss, Muscle Gain, Maintenance (3 standard fitness goals aligned with calorie adjustments)
- Q: Should a unified Data Retention Table be created to clarify exactly what data is deleted when? → A: Yes - Create authoritative table specifying retention periods for all data types to eliminate contradictions
- Q: What should the delivery email subject line and primary CTA button text be? → A: Subject: "Your Custom Keto Plan - Ready to Transform!" / CTA Button: "Get Started Now" (motivational tone aligned with fitness goals)
- Q: What data structure should be used to store the food preference summary? → A: JSON object stored in JSONB column: {excluded_foods: [], preferred_proteins: [], dietary_restrictions: string}
- Q: What framework should be used for AI meal plan generation agent? → A: OpenAI Agents SDK (Python) with OpenAIChatCompletionsModel; use Gemini API (via AsyncOpenAI with custom base_url) for dev/testing, OpenAI API for production; enables structured agent workflows
- Q: Should all Paddle payment methods be enabled or restricted to specific methods? → A: Enable ALL payment methods (credit/debit cards, Apple Pay, Google Pay, local methods like iDEAL and Alipay); maximizes conversion rate by allowing users to pay with preferred method; no restrictions
- Q: Final spec/constitution verification - any remaining unclear or contradictory points? → A: Fixed 8 medium issues for 200% clarity: (1) Constitution formula Harris-Benedict→Mifflin-St Jeor, (2) Activity label "Couch Potato"→"Sedentary", (3) Food icons: 64x64px SVG colored (React Icons/Lucide), (4) Recovery email: "Request Magic Link" + "Create Free Account" CTAs, (5) OpenAI Agents SDK pinned: >=0.1.0,<1.0.0, (6) Quiz cross-device: no sync (device-specific), (7) Blob URLs: Vercel Blob signed URLs (time-limited), (8) Alerts: Sentry email to project owner
- Q: Ultra-thorough final verification - are you absolutely certain there are no remaining gaps? → A: Fixed 4 final implementation gaps for 200% certainty: (1) Food preference summary derivation: excluded_foods from Steps 3-16 not selected, preferred_proteins from Steps 3,4,9 selected, dietary_restrictions from Step 17 (FR-A-014), (2) Quiz validation: 0-unlimited selections per food step, warning if <3 total items (FR-Q-017), (3) Paddle checkout: modal overlay using Paddle.js not redirect (FR-P-003), (4) Transaction boundaries: quiz save + meal plan creation atomic, payment + AI trigger atomic, PDF + email atomic (FR-Q-018)

### Session 2025-12-28
- Q: How should the system prevent users from entering incorrect email addresses before payment? → A: Send verification code to email before enabling payment button (user must enter 6-digit code to verify email ownership)
- Q: What mechanism should ensure webhook idempotency to prevent duplicate payment processing? → A: Use payment_id with database unique constraint (prevents duplicate processing at DB level)
- Q: How should the system prevent users from accidentally making duplicate payments for the same meal plan? → A: Block duplicate payments by email + timestamp window (prevent if same email paid <10 minutes ago)
- Q: What should happen if payment webhook arrives but quiz_responses data is missing or corrupted? → A: Verify quiz_responses exists; if missing, queue for manual resolution + send recovery email to user
- Q: What refund policy should apply if both AI providers fail and meal plan cannot be generated? → A: 4-hour SLA with automatic refund if unmet (clear user expectation, prevents chargebacks)
- Q: How should webhook handler prevent race condition when quiz save transaction is still in-flight? → A: Poll/retry for 3 seconds with 500ms intervals before manual resolution (prevents false positives)
- Q: What should happen when Paddle sends chargeback webhook for disputed payment? → A: Log chargeback, keep PDF accessible, blacklist email for 90 days to prevent re-purchase
- Q: What are the email verification code operational details (expiry, resend limits, fallback)? → A: 10-minute expiry, unlimited resends with 60-second cooldown, fallback to support contact if email fails
- Q: What should happen to quiz_responses records if user never completes payment (abandons at Paddle modal)? → A: Delete unpaid quiz_responses after 7 days (prevents database bloat while allowing reasonable window for payment completion)
- Q: How should system validate AI output structural integrity beyond keto compliance? → A: Validate structure before PDF generation; retry AI once if invalid; fail to manual resolution if still invalid

### Session 2025-12-29 (Security Audit & Loophole Fixes)
- Q: How should system prevent email verification bypass where user verifies email A then changes to email B in Paddle modal? → A: Lock email field in Paddle checkout modal (readonly), pass verified email as immutable customer_email parameter; prevent any email modification during checkout flow
- Q: How should system prevent blacklist bypass using Gmail aliases (user+1@gmail.com, user+2@gmail.com)? → A: Normalize all emails before checks: remove dots and +tags for Gmail/Googlemail, lowercase all; store both original (for communications) and normalized (for lookups) in database with indexes
- Q: What are the complete operational specifications for manual_resolution queue (monitoring, SLA tracking, escalation)? → A: Implement as database table with fields (id, created_at, issue_type, payment_id, status, sla_deadline); Sentry alerts on creation; scheduled job every 15min checks SLA breaches and triggers auto-refunds; admin dashboard at /admin/manual-resolution
- Q: How should system prevent account creation email mismatch where user creates account with different email than purchase? → A: Enforce account email must match purchase email (readonly field, pre-filled); account creation link includes signed token encoding purchase_email; validate match during account creation
- Q: What security controls should magic links implement beyond basic expiration? → A: Single-use enforcement (invalidate on first use), IP logging (warn on mismatch), 256-bit token entropy, rate limit 3 requests per email per 24h; token includes email hash, timestamps, signature
- Q: How should users recover PDF if email delivery fails AND they haven't created optional account? → A: Public recovery page at /recover-plan accepts email input, sends magic link if purchase found in last 90 days; rate limit 5 requests per IP per hour
- Q: How should system prevent concurrent purchase race condition (two simultaneous payments from same user)? → A: Distributed lock (Redis SETNX, 60s TTL) on normalized_email before checkout; if lock fails, display error; check for successful payment in last 10 minutes using normalized_email
- Q: How should system prevent refund gaming where user intentionally causes AI failures to get repeated refunds? → A: Track refund count per normalized_email; ≥2 refunds in 90 days → flag 3rd purchase for manual review (no auto-refund); ≥3 refunds → block purchases for 30 days
- Q: What maximum retry limits should apply to AI validation to prevent infinite loops? → A: Keto compliance validation: max 2 retries (3 total attempts); structural validation: max 1 retry (2 total attempts); route to manual_resolution after retry exhaustion
- Q: Should quiz save race condition polling window be extended beyond 3 seconds? → A: Increase to 5 seconds (10 retries × 500ms intervals) to handle DB latency spikes while maintaining reasonable webhook timeout
- Q: What is the exact calculation order for calorie floor enforcement? → A: (1) Calculate BMR, (2) Apply activity multiplier, (3) Apply goal adjustment, (4) Clamp to minimum (1200F/1500M), (5) Log warning if clamped, (6) Display user warning
- Q: What identifier should download rate limiting use to balance security and UX? → A: Authenticated users: limit by user_id; magic link users: limit by email+IP hash; exclude downloads within first 5 minutes of delivery (allow accidental re-clicks)
- Q: Should webhook timestamp validation be added to prevent replay attacks? → A: Verify webhook timestamp in addition to HMAC signature; reject if |current_time - webhook_time| > 5 minutes; alert on >3 failures per hour
- Q: What is the exact PDF deletion timing to avoid user confusion on day 90? → A: PDFs deleted after 90 days + 24 hour grace period (total 91 days from creation); user can access anytime on day 90; deletion job runs daily at 00:00 UTC
- Q: Should Step 17 dietary restrictions field warn users about health data retention? → A: Display warning above input: "Privacy Notice: Enter only food preferences. Do NOT include medical diagnoses. This information is retained for 90 days."
- Q: Is 3-item minimum food selection sufficient for 30-day meal plan variety? → A: Increase to 10-item minimum (blocking error); 10-14 items shows warning; ≥15 items no warning; ensures minimum viable variety for AI
- Q: Should Paddle payment method refund compatibility be verified before enabling all payment methods? → A: Verify Paddle API supports automatic refunds for all enabled methods; document compatibility matrix in ADR; local methods requiring manual refunds route to manual_resolution queue
- Q: Should cross-device quiz behavior be explicitly documented for user clarity? → A: Add warning on quiz start page: "Your quiz progress is saved only on this device. If you switch devices, you'll need to start over." Acceptable for MVP given localStorage architecture
- Q: Should authentication be required before quiz starts to enable better tracking and cross-device sync? → A: Hybrid approach prioritizing revenue: (1) Quiz starts without auth (low friction entry), (2) Optional "Save Progress" prompt after Step 8-10 allowing mid-quiz account creation, (3) Users who create account get cross-device sync and incremental DB saves, (4) Users who skip continue with localStorage (current flow), (5) Email verification before payment (skip if already verified during mid-quiz signup), (6) Strong post-purchase account creation prompt; balances conversion optimization with progressive user engagement

### Session 2026-01-01 (Specification Gap Resolution)
- Q: How should the system authenticate admin access to the manual resolution dashboard at /admin/manual-resolution? → A: API key authentication with IP whitelist; admin includes X-API-Key header in requests, server validates against ADMIN_API_KEY environment variable and checks source IP against ADMIN_IP_WHITELIST (comma-separated IPs in env var); simple to implement, no session management overhead, secure for internal admin tool
- Q: How should the system handle Vercel Blob signed URL expiry (typically 1-7 days) versus 90-day PDF retention period to prevent access issues? → A: Generate fresh signed URLs on-demand when user requests download; store permanent blob path (not signed URL) in database; when user clicks download link (via email, dashboard, magic link), backend generates fresh signed URL with 1-hour expiry and returns it; prevents URL expiry mismatch, maintains security, ensures PDF always accessible during 90-day retention
- Q: Should email normalization be extended to non-Gmail providers (Yahoo+, Outlook+, Protonmail aliases) to prevent bypass? → A: Gmail-only normalization (current FR-P-010 spec); normalize only Gmail/Googlemail addresses (remove dots, strip +tags, lowercase); accept bypass risk for other providers as acceptable for MVP; rationale: Gmail is dominant provider (~30% market share), plus-tag aliasing primarily Gmail feature, other providers have proprietary alias systems harder to normalize reliably, diminishing returns vs complexity tradeoff
- Q: What happens if user verifies email, opens Paddle checkout modal, then closes it without paying (modal abandonment)? → A: Quiz data and email verification remain valid for 24 hours; user can return to review screen and proceed to payment without re-verification; after 24 hours, email verification expires and user must re-verify (new 6-digit code) before payment; quiz data persists for 7 days (per FR-Q-011 unpaid quiz cleanup); reduces friction for legitimate users who got interrupted while maintaining security
- Q: How should the system handle theoretical race condition where Redis lock expires (60s TTL) between two devices and both acquire lock before 10-minute duplicate payment check? → A: Accept race condition risk as acceptable for MVP (current FR-P-007 spec); rationale: (1) Exploit window is narrow (must time two payments precisely within 60s), (2) 10-minute duplicate payment check provides additional protection layer, (3) True simultaneous payments from different devices are extremely rare in practice, (4) Additional complexity (distributed transactions, extended locks) adds minimal value for MVP, (5) Can monitor via payment analytics and address post-MVP if becomes real issue; current two-layer protection (Redis lock + 10-min DB check) sufficient for launch


## User Scenarios & Testing

### User Story 1 - Complete Quiz End-to-End (Priority: P1)

**As a** health-conscious user interested in keto diet **I want to** complete a 20-step personalized quiz without abandonment **So that** I receive a customized meal plan tailored to my preferences and needs

**Why this priority**: This is the core value proposition. Without completing the quiz, users cannot generate meal plans. P1 because quiz completion directly enables all downstream features (payment, AI generation, PDF delivery).

**Independent Test**: User can start quiz without authentication (low friction), answer all 20 questions with validation feedback, optionally create account at Step 10 to save progress across devices, navigate back to correct previous answers, submit without data loss, and proceed to payment. Success = completed quiz data stored in database ready for payment processing.

**Hybrid Auth Flow**: User has TWO paths: (1) **Unauthenticated path**: complete quiz using localStorage, verify email before payment; (2) **Authenticated path**: create account at Step 10 prompt, get cross-device sync and incremental saves, skip email verification before payment (already verified during signup).

**Acceptance Scenarios**:

1. **Given** user is on step 1 of quiz, **When** user selects gender, **Then** selection is saved and Next button enables step 2
2. **Given** user is on step 5 (meat preferences), **When** user deselects options and clicks Next, **Then** selections saved and user advances
3. **Given** user is on step 15 (beverages), **When** user clicks Back, **Then** previous data restored and user returns to step 14
4. **Given** user is on step 20 (biometrics), **When** user enters age, weight, height, goal, **Then** all fields validate (age 18-100, weight >0, height >0) and submit enables
5. **Given** user completes all 20 steps with valid data, **When** user clicks Submit, **Then** progress indicator shows "Step 20 of 20" and quiz response stored in database

---

### User Story 2 - Navigate Backward Through Quiz (Priority: P2)

**As a** user completing the quiz **I want to** go back and correct answers on previous steps **So that** I can ensure all my preferences are accurately captured before payment

**Why this priority**: Users expect ability to review/correct answers. P2 because it improves completion rate but quiz can function without it (users can abandon and restart). High priority for UX polish.

**Independent Test**: User can click Back from any step (2-20), previous data is fully restored, user can modify answer, click Next and new data persists. Success = back navigation preserves all data without loss.

**Acceptance Scenarios**:

1. **Given** user is on step 10 and previously selected 5 vegetables, **When** user clicks Back twice to step 8, **Then** all data from steps 9-10 preserved and user can see step 8 content
2. **Given** user modified step 8 (vegetables) from the back-navigation, **When** user clicks Next twice, **Then** modified vegetable selection is retained in quiz response
3. **Given** user is on step 1, **When** user clicks Back, **Then** Back button is disabled/hidden (no step 0)

---

### User Story 3 - Privacy Messaging & Data Reassurance (Priority: P2)

**As a** user providing health and biometric information **I want to** see clear privacy reassurance messaging **So that** I trust the product with my personal health data

**Why this priority**: Users hesitate to share health data without reassurance. P2 because it directly impacts conversion at payment funnel but doesn't block core functionality. Trust driver.

**Independent Test**: Step 20 displays lock icon + "100% Private & Confidential" messaging, user sees privacy policy link, messaging explains data deletion after PDF delivery. Success = user completes biometric data entry with confidence.

**Acceptance Scenarios**:

1. **Given** user reaches step 20, **When** step loads, **Then** lock icon displays above biometric data fields with text "100% Private & Confidential"
2. **Given** user is on step 20, **When** user hovers over lock icon, **Then** tooltip explains data deletion policy
3. **Given** user is on step 20, **When** user clicks privacy policy link, **Then** new tab opens with full privacy/GDPR information

---

### User Story 4 - PDF Recovery via Account or Magic Link (Priority: P3)

**As a** user who lost or deleted the original meal plan email **I want to** recover my PDF using either optional account login or magic email link **So that** I don't lose access to my purchased meal plan

**Why this priority**: Reduces support burden but not essential for MVP launch. P3 because recovery is a nice-to-have that prevents support tickets but doesn't impact core product.

**Independent Test**: User receives magic link in recovery request email, clicking link grants 24-hour PDF download access without password. User can also login and see "Download My Plan" button. Success = PDF accessible for 90 days via multiple recovery methods.

**Acceptance Scenarios**:

1. **Given** user requests PDF recovery via email, **When** recovery email arrives, **Then** magic link works and PDF downloads without login
2. **Given** user creates account/logs in with email, **When** dashboard loads, **Then** "Download My Plan" button displays with PDF availability status
3. **Given** user uses magic link, **When** 24 hours pass, **Then** link expires and user must request new link or login to access PDF

---

### User Story 5 - Smooth UI Animations & Loading States (Priority: P3)

**As a** user completing the quiz and waiting for meal plan generation **I want to** see smooth animations and clear loading progress **So that** the experience feels professional and I understand processing is occurring

**Why this priority**: Polish feature that improves perception but not essential for MVP. P3 because animations are nice-to-have; product works without them but feels more professional with them.

**Independent Test**: Quiz step transitions animate smoothly (Framer Motion, no jank), loading screen shows multi-step progress messages, success confirmation animates. Success = all transitions <16ms (60fps).

**Acceptance Scenarios**:

1. **Given** user clicks Next button, **When** new quiz step loads, **Then** transition animates smoothly over 300-400ms with ease-in-out
2. **Given** user submits quiz and payment succeeds, **When** loading screen appears, **Then** progress displays sequence: "Analyzing data..." → "Calculating nutritional profile..." → "Selecting recipes..." → "Generating your 30-day plan..."
3. **Given** meal plan generation completes, **When** success message appears, **Then** message animates in smoothly and "Download PDF" button scales slightly

---

## Edge Cases

1. **User submits quiz without email**: System displays error "Email is required" and prevents submission; user cannot proceed to payment.

2. **AI API fails during meal plan generation**: System implements intelligent retry/fallback: retries OpenAI 3x for transient errors (timeout, rate limit, 5xx); immediately falls back to Gemini for auth/quota errors; if both providers fail, user receives recovery email with regeneration link and 4-hour SLA commitment; if meal plan not delivered within 4 hours, system automatically initiates refund via Paddle API and notifies user.

3. **Payment webhook arrives but quiz_responses data is missing or corrupted**: Webhook handler verifies quiz_responses record exists using email from payment; if missing, creates manual_resolution queue entry, sends recovery email to user ("We received your payment but encountered a data issue. Our team will generate your plan within 4 hours."), and alerts support team; prevents revenue loss while maintaining user trust.

4. **Email delivery fails** (e.g., spam filter, invalid domain): System retries sending with Resend (3 attempts) and stores failure in database; user can request re-send via account dashboard; fallback: PDF remains in blob storage for 90-day recovery.

5. **User navigates back after payment but before PDF generation completes**: Loading screen remains visible; PDF is generated and sent asynchronously; user receives email with PDF regardless of browser state.

6. **Blob storage reaches 80% of free tier capacity**: Monitoring alert triggers; system must evaluate cleanup strategy (archive old PDFs or upgrade tier); production does not break.

7. **User submits quiz with contradictory food preferences** (e.g., "no vegetables" and "wants vegetable-based meals"): AI prompt handles gracefully by requesting meals matching high-priority preferences; system surfaces warning to user if AI detects conflict.

8. **User refreshes page multiple times during quiz completion**: Quiz state persists via localStorage; data restored on page reload within same browser; no database interaction until final submission; closing browser/clearing cache loses progress (acceptable for MVP).

9. **Mifflin-St Jeor calorie calculation with -400 kcal deficit results in target <1200 (women) or <1500 (men)**: System enforces minimum safe thresholds and adjusts target to safe minimum; user receives warning: "Your goal requires an aggressive calorie target. We've set a safe minimum of 1200/1500 kcal."

---

## Requirements

### Functional Requirements by Category

#### Quiz (FR-Q-001 to FR-Q-015)

- **FR-Q-001**: System MUST display 20-step progressive form with one question per page
- **FR-Q-002**: Steps 1-2 MUST allow gender selection (Female/Male) and activity level selection (Sedentary, Lightly Active, Moderately Active, Very Active, Super Active) with radio/select inputs
- **FR-Q-003**: Steps 3-17 MUST present multi-select checkboxes for food categories with visual food icons (64x64px)
- **FR-Q-004**: Step 17 MUST include free-text field for dietary restrictions (max 500 characters) with prominent warning displayed above input field: "⚠️ Privacy Notice: Enter only food preferences and dietary needs. Do NOT include medical diagnoses, health conditions, or personal health information. This information is retained for 90 days."
- **FR-Q-005**: Steps 18-19 MUST allow eating frequency selection and personal trait checkboxes (5 options)
- **FR-Q-006**: Step 20 MUST collect age, weight (kg/lbs selector), height (cm/ft-in selector), goal selection (Weight Loss, Muscle Gain, or Maintenance), with privacy messaging
- **FR-Q-007**: All steps MUST include inline validation (React Hook Form + Zod) with user-friendly error messages
- **FR-Q-008**: System MUST display progress "Step X of 20" at top of quiz container and update on transitions
- **FR-Q-009**: Back/Next buttons MUST preserve all entered data with hybrid persistence strategy: (1) **Unauthenticated users**: React state + localStorage backup (device-specific, no cross-device sync); (2) **Authenticated users** (created account via FR-Q-020 mid-quiz prompt): React state + incremental database saves after each step (cross-device sync enabled); (3) No data loss on navigation within same session; (4) Users warned on quiz start page: "Your quiz progress is saved only on this device. Create a free account during the quiz to save progress across devices."; (5) Unauthenticated users switching devices must restart quiz; (6) Authenticated users can resume quiz from any device using last saved step; (7) Duplicate payment prevention (FR-P-007) enforces only one purchase per 10-minute window regardless of device/auth status
- **FR-Q-010**: Quiz submission MUST display review screen with quiz summary and calculated calorie target, then "Proceed to Payment" button triggers Paddle checkout
- **FR-Q-011**: System MUST save quiz responses to database with hybrid strategy based on auth status: (1) **Unauthenticated users**: save to database only on final submission (step 20 complete); no incremental saves during progression; (2) **Authenticated users** (created account via FR-Q-020): incremental saves to database after each step completion (enables cross-device resume per FR-Q-009); (3) All quiz responses follow data retention per Data Retention Policy table (quiz responses deleted 24h after PDF delivery, preference summary retained 90d); (4) Authenticated users resuming quiz on different device load last saved step from database
- **FR-Q-012**: Form validation MUST reject submission if required fields empty with clear error message
- **FR-Q-013**: System MUST validate: age 18-100 years, weight 30-500 lbs (13.6-227 kg), height 122-229 cm metric or 48-90 inches imperial (4'0"-7'6")
- **FR-Q-014**: UI MUST be mobile-responsive (tested 360px width) with touch buttons ≥44px height
- **FR-Q-015**: Quiz completion timestamps logged for engagement monitoring and analytics
- **FR-Q-016**: Review screen MUST display quiz summary (selected preferences count), calculated calorie target with breakdown (BMR, activity, goal adjustment), and prominent "Proceed to Payment" CTA button
- **FR-Q-017**: Food preference steps (Steps 3-16) validation rules: minimum 0 selections allowed per individual step (user can skip entire category), no maximum limit (user can select all); system MUST validate total selections across ALL food steps (3-16) before allowing quiz submission: (1) If total selections < 10 items, display blocking error (cannot proceed): "Please select at least 10 food items across all categories to generate a personalized meal plan with sufficient variety"; (2) If total selections 10-14 items, display warning (can proceed): "You've selected {count} items. Selecting more foods (15+) will create more varied meal plans."; (3) If total selections ≥15 items, no warning; 10-item minimum ensures minimum viable variety for AI
- **FR-Q-018**: Database transaction boundaries MUST ensure atomicity: (1) Quiz submission: save quiz_responses + create meal_plans record (both succeed or both fail); (2) Payment webhook: update payment_status + trigger AI generation queue (atomic); (3) PDF delivery: update pdf_blob_url + update email_delivery_status (atomic); rollback on failure with retry capability
- **FR-Q-019**: Email verification MUST be completed before payment button is enabled with auth-aware logic: (1) **Unauthenticated users**: system sends 6-digit verification code to user-provided email on Step 20; user must enter correct code to verify email ownership before payment; (2) **Authenticated users** (created account via FR-Q-020): email already verified during signup, skip 6-digit code verification; (3) Verification code expires after 10 minutes; unlimited resend capability with 60-second cooldown between requests (prevents spam); (4) Once verified, email verification status remains valid for 24 hours (allows user to abandon Paddle modal and return without re-verification); after 24 hours, verification expires and user must re-verify; (5) If email delivery fails repeatedly, display support contact button with message "Having trouble? Contact support"; prevents payment with invalid/typo email addresses while providing escape hatch for legitimate users
- **FR-Q-020**: System MUST display optional "Save Progress" prompt after user completes Step 10 (mid-quiz checkpoint) with following behavior: (1) **Trigger condition**: user reaches Step 11, has NOT yet created account, prompt appears as non-blocking modal overlay; (2) **Prompt copy**: "Want to save your progress and continue on any device? Create a free account (30 seconds)" with two CTAs: "Create Account" (primary) and "Skip" (secondary text link); (3) **Create Account flow**: modal shows email + password fields, "Create Account" button; upon submission, verify email via 6-digit code (same as FR-Q-019 but during quiz), create user account, save current quiz progress to database (Steps 1-10), enable incremental saves (per FR-Q-011), close modal, continue to Step 11; (4) **Skip flow**: close modal, continue with localStorage (per FR-Q-009 unauthenticated flow); (5) **Prompt frequency**: show once per quiz session; if user skips, do not show again; (6) **Mobile UX**: full-screen takeover on mobile (<768px), modal on desktop; (7) **Conversion tracking**: log prompt shown, account created, skipped events for analytics

#### Calorie Calculation (FR-C-001 to FR-C-006)

- **FR-C-001**: System MUST calculate BMR using Mifflin-St Jeor formula: Men: (10 × weight_kg) + (6.25 × height_cm) - (5 × age) + 5; Women: (10 × weight_kg) + (6.25 × height_cm) - (5 × age) - 161
- **FR-C-002**: System MUST apply activity multiplier to BMR based on user selection: Sedentary (1.2), Lightly Active (1.375), Moderately Active (1.55), Very Active (1.725), Super Active (1.9)
- **FR-C-003**: System MUST adjust for goal using fixed values: Weight Loss = -400 kcal deficit, Muscle Gain = +250 kcal surplus, Maintenance = 0 kcal adjustment
- **FR-C-004**: System MUST enforce calorie minimums (Women ≥1200 kcal, Men ≥1500 kcal) using following calculation order: (1) Calculate BMR (per FR-C-001); (2) Apply activity multiplier (per FR-C-002); (3) Apply goal adjustment (per FR-C-003): Weight Loss -400, Muscle Gain +250, Maintenance 0; (4) Check if result < minimum threshold; (5) If below minimum, clamp to minimum and log warning with details: "User {email} calculated {result} kcal but clamped to safe minimum {minimum} kcal. Original: BMR={bmr}, Activity={multiplier}, Goal={adjustment}"; (6) Display warning to user: "Your goal requires an aggressive calorie target. We've set a safe minimum of {minimum} kcal based on established nutritional guidelines."
- **FR-C-005**: Calorie target MUST be stored in database and passed to AI meal plan prompt
- **FR-C-006**: Generated meal plan MUST display daily calorie target and macronutrient targets for transparency

#### Payment (FR-P-001 to FR-P-006)

- **FR-P-001**: System MUST integrate Paddle for all payment processing with ALL supported payment methods enabled (credit/debit cards, Apple Pay, Google Pay, local payment methods like iDEAL and Alipay); maximizes conversion rate by allowing users to pay with preferred method; Paddle handles PCI compliance; no credit card data stored locally
- **FR-P-002**: Paddle webhook MUST verify HMAC-SHA256 signature using webhook secret (environment variable) AND webhook timestamp before processing: (1) Extract timestamp from webhook payload (Paddle includes event creation timestamp); (2) Reject webhooks where ABS(current_time - webhook_timestamp) > 5 minutes; (3) Return 401 with body: {"error": "Webhook timestamp too old or too far in future"}; (4) Log rejection to Sentry with timestamp delta for monitoring; (5) Continue with idempotency check using payment_id unique constraint (prevents duplicate processing); (6) Alert on >3 timestamp validation failures per hour (indicates potential replay attack or clock skew); duplicate webhooks return 200 without re-processing
- **FR-P-003**: Quiz submission MUST display Paddle Checkout as modal overlay (not redirect) using Paddle.js; modal appears on top of review screen with product details and user email PRE-FILLED AND LOCKED (readonly field); verified email from FR-Q-019 MUST be passed as immutable `customer_email` parameter to Paddle.Checkout.open(); Paddle must NOT allow email modification during checkout; user remains on site during payment flow; modal dismissal returns user to review screen; any attempt to modify email in Paddle returns user to Step 20 with error "Email cannot be changed after verification. Use verified email: {email}"
- **FR-P-004**: Payment confirmation MUST be logged with timestamp and Paddle transaction ID
- **FR-P-005**: Failed payment MUST allow retry without re-entering quiz data; session preserved
- **FR-P-006**: All payment events logged for accounting; no sensitive payment details in logs
- **FR-P-007**: System MUST prevent duplicate payments using normalized_email (per FR-P-010) with following controls: (1) Before initiating Paddle checkout, acquire distributed lock (Redis: SETNX with 60s TTL) on key "payment_lock:{normalized_email}"; if lock acquisition fails, display error: "A payment is already in progress for this email. Please wait 60 seconds or complete your existing payment"; (2) Check if normalized_email has successful payment where created_at > NOW() - INTERVAL '10 minutes'; (3) If duplicate detected, block payment with message: "You recently purchased a meal plan. Please check your email or contact support"; (4) Lock released automatically after 60 seconds or upon payment webhook success/failure; allows legitimate repurchases after 10-minute cooldown period
- **FR-P-008**: Webhook handler MUST verify quiz_responses record exists before triggering AI generation; if not found on first check, poll/retry up to 10 times with 500ms intervals (total 5-second grace period, increased from 3s) to prevent race condition with in-flight quiz save transaction; if still missing after retries, create manual_resolution queue entry (per FR-M-001), send recovery email to user (per FR-M-003), and trigger 4-hour SLA (per FR-M-004); prevents both race condition false positives and orphaned payments
- **FR-P-009**: System MUST handle Paddle chargeback webhooks by logging chargeback event (payment_id, email, timestamp, reason), adding normalized_email (per FR-P-010) to blacklist table with 90-day TTL to prevent re-purchase, and alerting finance team via Sentry; PDF remains accessible to avoid complex URL revocation; accepts small revenue loss for MVP simplicity; blacklist check occurs during duplicate payment validation (FR-P-007) using normalized_email
- **FR-P-010**: Email normalization MUST be applied before ALL email-based checks (blacklist, duplicate payment, account lookup) to prevent alias bypasses: (1) Gmail normalization: remove all dots (.) before @ symbol, strip +tag suffixes (user.name+tag@gmail.com → username@gmail.com); (2) Googlemail.com → gmail.com conversion; (3) Lowercase all email addresses; (4) Store both original email (for communications) and normalized_email (for lookups) in database with index on normalized_email; (5) Blacklist check (FR-P-009), duplicate payment check (FR-P-007), and account lookup (FR-R-001) MUST use normalized_email for comparison
- **FR-P-011**: Refund abuse prevention MUST implement following controls: (1) Track refund count per normalized_email (per FR-P-010) in last 90 days; (2) If normalized_email has ≥2 automatic refunds in 90 days, third purchase MUST be flagged for manual review before AI generation (prevent auto-refund loop); (3) Flagged purchases route to manual_resolution queue immediately with note "Repeat refund user"; (4) Manual resolution team must review quiz data for malicious patterns before generating plan; (5) If normalized_email has ≥3 refunds in 90 days, block future purchases for 30 days with message: "Due to technical issues with your previous purchases, please contact support to proceed"; (6) Log all refund patterns to Sentry for fraud analysis; (7) After successful delivery to flagged user, reset flag (legitimate user who had bad luck)
- **FR-P-012**: Automatic refund implementation (per FR-A-011 4-hour SLA failure) MUST verify Paddle API refund support for payment method before triggering: (1) Paddle API supports automatic refunds for: credit/debit cards, Apple Pay, Google Pay; (2) Paddle API may NOT support automatic refund for some local methods (iDEAL, Alipay, bank transfers); (3) Before triggering refund, check payment_method from Paddle webhook metadata; (4) If payment_method supports automatic refund, call Paddle refund API; (5) If payment_method does NOT support automatic refund, create manual_resolution queue entry with issue_type='manual_refund_required', alert finance team via Sentry, send email to user: "We apologize for the delay. Your refund will be processed manually within 24 hours to your {payment_method}"; (6) Document refund compatibility matrix in ADR during implementation planning
- **FR-P-013**: System MUST store payment transaction metadata in payment_transactions table upon successful webhook processing: (1) Extract from Paddle webhook: payment_id, amount, currency, payment_method, customer_email, paddle_created_at timestamp; (2) Normalize customer_email per FR-P-010; (3) Create payment_transactions record with fields: id (UUID), payment_id (unique), meal_plan_id (FK, nullable initially), amount (DECIMAL), currency (VARCHAR 3), payment_method (VARCHAR 50), payment_status (default 'succeeded'), paddle_created_at, webhook_received_at (system timestamp), customer_email, normalized_email; (4) Link to meal_plans record via meal_plan_id FK once created; (5) Update payment_status to 'refunded' on refund webhooks (FR-P-012) and 'chargeback' on chargeback webhooks (FR-P-009); (6) Retain records for 1 year for compliance/audit (matching FR-M-006); (7) Enable analytics queries (revenue by payment method, currency distribution, daily totals) and support investigations without external API calls; (8) NEVER store PCI-sensitive data (card numbers, CVV, expiration dates, billing addresses); Paddle webhook only provides safe transaction metadata

#### Manual Resolution (FR-M-001 to FR-M-006)

- **FR-M-001**: System MUST implement manual_resolution queue as database table with fields: id (UUID), created_at (timestamp), issue_type (enum: missing_quiz_data, ai_validation_failed, email_delivery_failed, manual_refund_required), payment_id, user_email, normalized_email, status (enum: pending, in_progress, resolved, escalated, sla_missed_refunded), assigned_to, resolution_notes, sla_deadline (created_at + 4 hours), resolved_at
- **FR-M-002**: Manual resolution queue entries MUST trigger immediate Sentry alert to project owner with payload: issue_type, user_email, payment_id, time_remaining_to_sla
- **FR-M-003**: System MUST send recovery email to user upon manual queue entry with message: "We received your payment but encountered a technical issue. Our team is generating your meal plan manually. You'll receive it within 4 hours (by {deadline_time} UTC). If not delivered by then, you'll receive an automatic full refund."
- **FR-M-004**: Scheduled job MUST run every 15 minutes checking for manual_resolution entries where current_time > sla_deadline AND status != resolved; if found, automatically trigger Paddle refund API call (per FR-P-012), update payment status to 'refunded', send refund notification email, update manual_resolution status to 'sla_missed_refunded', and create high-priority Sentry alert
- **FR-M-005**: Manual resolution dashboard MUST be accessible at /admin/manual-resolution with API key authentication and IP whitelist protection: (1) Admin requests MUST include X-API-Key header; (2) Backend validates header value against ADMIN_API_KEY environment variable; (3) Backend validates source IP against ADMIN_IP_WHITELIST environment variable (comma-separated list of allowed IPs); (4) If validation fails, return 401 Unauthorized; (5) Dashboard displays: pending count, time to SLA breach for each entry, quick actions (mark resolved, trigger manual PDF generation, issue refund); (6) No session management required (stateless authentication)
- **FR-M-006**: Manual resolution entries MUST be retained for 1 year for compliance audit; aggregate metrics (total entries, resolution rate, SLA miss rate) logged monthly

#### AI Generation (FR-A-001 to FR-A-011)

- **FR-A-001**: System MUST use OpenAI Agents SDK with OpenAIChatCompletionsModel to create meal plan generation agent; configure AsyncOpenAI client with custom base_url for Gemini API (dev/testing: base_url="https://generativelanguage.googleapis.com/v1beta", api_key=GEMINI_API_KEY); use standard OpenAI API client for production (api_key=OPENAI_API_KEY); implement automatic fallback to Gemini if OpenAI fails after 3 retries
- **FR-A-002**: AI prompt MUST enforce keto compliance: <30g net carbs/day, 65-75% fat, 20-30% protein
- **FR-A-003**: AI prompt MUST request 30-day plan with 3 meals per day (breakfast, lunch, dinner) and NO recipe repetition within same plan
- **FR-A-004**: AI prompt MUST incorporate user food preferences and exclude disliked foods
- **FR-A-005**: AI prompt MUST specify practical constraints (≤10 ingredients/meal, ≤30 min prep time)
- **FR-A-006**: AI generation MUST complete within 20 seconds (p95); timeout triggers retry with exponential backoff
- **FR-A-007**: AI response MUST be validated for keto compliance (any day >30g net carbs) AND structural integrity (per FR-A-015); validation failures trigger retry with maximum retry limits: (1) Keto compliance failures: retry up to 2 times (3 total attempts); (2) Structural integrity failures: retry up to 1 time (2 total attempts); (3) Retry strategy: regenerate with same prompt + appended guidance: "CRITICAL: Previous attempt failed validation because {reason}. You MUST ensure {specific_requirement}"; (4) If all retries exhausted for either validation type, route to manual_resolution queue (per FR-M-001) with 4-hour SLA; (5) Log all validation failures to Sentry with quiz data hash (not full quiz) for pattern analysis
- **FR-A-008**: AI output MUST include motivational content (keto tips, hydration reminders, electrolyte guidance)
- **FR-A-009**: System MUST log AI metadata (timestamp, user_id, model, tokens) but NOT full responses
- **FR-A-010**: Generated meal plan full text deleted after PDF delivery; all data retention per Data Retention Policy table (metadata retained 90 days, biometric data deleted after 24h, preference summary retained with metadata)
- **FR-A-011**: Retry logic with exponential backoff (2s, 4s, 8s); Immediate fallback to Gemini on: auth errors, quota exceeded, invalid API key; Retry OpenAI 3x on: timeout (>20s), rate limit (429), server errors (500-503); If Gemini also fails after 3 retries, send recovery email with 4-hour SLA; if meal plan not delivered within 4 hours from payment, system automatically initiates refund via Paddle API and sends refund notification email
- **FR-A-012**: AI prompt MUST request 4 weekly shopping lists organized by ingredient category (proteins, vegetables, dairy, fats, pantry staples, seasonings) with aggregated quantities
- **FR-A-013**: Meal plan generation MUST use OpenAI Agents SDK Agent class with @function_tool decorators for any helper functions; agent configured with name, instructions (keto compliance + user preferences), model (environment-based), and tools; executed via Runner.run() async pattern
- **FR-A-014**: Food preference summary JSONB derivation logic MUST follow this mapping: (1) excluded_foods[] = ALL food items NOT selected across Steps 3-16 (user dislikes/avoids); (2) preferred_proteins[] = ALL items selected from Steps 3 (meat), 4 (fish), 9 (shellfish) (user's protein preferences); (3) dietary_restrictions = free text from Step 17 (per FR-Q-004 privacy notice); summary enables AI personalization and support queries without retaining full quiz data; system does NOT perform medical data detection/filtering; user responsible for following FR-Q-004 privacy notice guidelines
- **FR-A-015**: System MUST validate AI output structural integrity before PDF generation: verify exactly 30 days present, each day contains exactly 3 meals (breakfast, lunch, dinner), all required nutritional fields populated, JSON structure parseable; if validation fails, retry AI generation once with same prompt (per FR-A-007 retry limits); if second attempt also fails, route to manual_resolution queue (per FR-M-001) with issue_type='ai_validation_failed', send recovery email (per FR-M-003), and trigger 4-hour SLA countdown (per FR-M-004); prevents delivery of incomplete or corrupt meal plans

#### PDF Generation & Storage (FR-D-001 to FR-D-008)

- **FR-D-001**: System MUST generate PDF with 30-day meal plan (3 meals per day: breakfast, lunch, dinner), macronutrient breakdown per meal, and 4 weekly shopping lists (Week 1-4) organized by ingredient category
- **FR-D-002**: PDF MUST include user data: name, goals, calorie target, macronutrient targets, generation date
- **FR-D-003**: PDF MUST display daily meals (breakfast, lunch, dinner) with macronutrient breakdown per meal and daily totals summing all 3 meals
- **FR-D-004**: PDF generation MUST complete within 20 seconds (p95); retry on timeout
- **FR-D-005**: PDF MUST be uploaded to Vercel Blob storage; system stores permanent blob path (not signed URL) in database for 90-day retention; provides secure access without exposing direct file paths
- **FR-D-006**: Blob path (permanent identifier, not time-limited signed URL) MUST be stored in database (pdf_blob_path field) for recovery capability; signed URLs generated on-demand when user requests download (per FR-R-003)
- **FR-D-007**: PDF MUST be delivered as email attachment (primary) + blob storage URL (recovery backup)
- **FR-D-008**: System MUST auto-delete PDFs older than 90 days; log deletion for compliance

#### Email Delivery (FR-E-001 to FR-E-005)

- **FR-E-001**: System MUST send transactional email to user with PDF attached upon successful payment
- **FR-E-002**: Email MUST include PDF download link (points to backend /api/download-pdf endpoint which generates fresh signed URL on-demand per FR-R-003), recovery instructions (magic link or account login), and optional account creation link ("Create account to access your dashboard anytime")
- **FR-E-003**: Email template MUST be professional, branded (green - **FR-E-003**: Email template MUST be professional, branded (green & white), mobile-responsive white), mobile-responsive; Subject line: "Your Custom Keto Plan - Ready to Transform!"; Primary CTA button: "Get Started Now"; body includes congratulations message, PDF attachment notice, and recovery instructions
- **FR-E-004**: Email sending MUST be idempotent; duplicate webhooks MUST NOT send multiple emails
- **FR-E-005**: Failed email MUST retry (3 attempts, exponential backoff: 2s, 4s, 8s); if all retries fail, create manual_resolution queue entry (per FR-M-001); user can request re-send via dashboard (if account created) OR via public recovery page (no account required, per FR-E-007)
- **FR-E-006**: Recovery instructions in delivery email MUST include: "Lost this email? You can re-download your plan anytime for 90 days:" followed by two options: (1) "Request Magic Link" button (sends 24-hour single-use download link to email), (2) "Create Free Account" link (enables dashboard login for PDF access); text must be clear and action-oriented
- **FR-E-007**: Public PDF recovery page MUST be available at /recover-plan for users who have not created accounts; page displays email input field with submit button; upon submission, system verifies email has successful purchase in last 90 days using normalized_email (per FR-P-010); if found, sends magic link to email (24-hour single-use per FR-R-002); if not found, displays "No meal plan found for this email. Please check your spelling or contact support"; rate limit: max 5 recovery requests per IP per hour (prevents enumeration attacks)

#### Recovery (FR-R-001 to FR-R-005)

- **FR-R-001**: System MUST provide THREE optional account creation touchpoints with progressive engagement strategy: (1) **Mid-quiz** (FR-Q-020): "Save Progress" prompt after Step 10 allowing account creation during quiz; email verified via 6-digit code during signup; (2) **Post-purchase**: prompt on success page ("Create account to access dashboard?" with Skip option); (3) **Email link**: link in delivery email; account creation at touchpoints (2) and (3) MUST use the same email address as the purchase (email field pre-filled and readonly); account creation link in delivery email MUST include signed token encoding purchase_email to enforce email match; if user attempts to create account with different email than purchase, display error: "Account must use purchase email: {purchase_email}"; during login, if user enters email that doesn't match any purchase, display: "No meal plan found for this email. Please use the email you used for purchase."; support email login and magic link authentication; account lookup uses normalized_email (per FR-P-010) for matching; users who created account mid-quiz (touchpoint 1) skip post-purchase prompt (already have account)
- **FR-R-002**: Magic link MUST grant 24-hour, single-use PDF access without password with following security controls: (1) Token format: cryptographically secure random 32-byte value (256-bit entropy); (2) Single-use enforcement: token MUST be invalidated in database immediately upon first use (set used_at timestamp); subsequent attempts with same token return 401 "Link already used"; (3) IP address logging: record IP address on token generation and first use; if IP differs, log warning but allow access (prevents legitimate mobile/WiFi switching from breaking UX); (4) Device fingerprinting (optional): collect User-Agent on generation and use; flag suspicious patterns (e.g., different OS/browser) but do not block; (5) Rate limiting: max 3 magic link requests per email per 24 hours (prevents spam/enumeration); (6) Expiration: token expires exactly 24 hours after generation (not first use); (7) Token must include: user_email hash, creation timestamp, expiration timestamp, signature
- **FR-R-003**: PDF download link MUST generate fresh Vercel Blob signed URLs on-demand (not pre-generated) to prevent unauthorized access: (1) Backend API endpoint /api/download-pdf accepts authenticated request (user session or magic link token); (2) Backend retrieves pdf_blob_path from database; (3) Backend generates fresh signed URL from Vercel Blob with 1-hour expiry; (4) Backend returns signed URL to client (redirect or JSON response); (5) Client downloads PDF using fresh signed URL; (6) Signed URLs automatically expire after 1 hour and cannot be guessed; (7) On-demand generation ensures URLs remain valid throughout 90-day retention period without URL expiry mismatch
- **FR-R-004**: Optional account dashboard MUST show "Download My Plan" button with availability status (90 days)
- **FR-R-005**: System MUST track download attempts and rate-limit using composite key: (1) For authenticated users (logged in): rate limit by user_id (max 10 downloads/24h); (2) For magic link users (not logged in): rate limit by email + IP address hash (max 10 downloads/24h); (3) Rate limit tracking stored in Redis with 24-hour TTL on key: "download_limit:{identifier}:{date}"; (4) If rate limit exceeded, display: "Download limit reached (10 per day). Please try again in {hours} hours."; (5) Exclude from rate limit: downloads within first 5 minutes of PDF delivery (allows immediate download if user clicks multiple times accidentally)

#### Performance (FR-F-001 to FR-F-005)

- **FR-F-001**: Quiz → Payment → AI → PDF → Email MUST complete within 90 seconds (p95)
- **FR-F-002**: AI meal plan generation MUST complete within 20 seconds (p95)
- **FR-F-003**: PDF generation MUST complete within 20 seconds (p95)
- **FR-F-004**: Database queries MUST complete within 500ms (p95); use indexes on email, payment_id, user_id
- **FR-F-005**: Frontend quiz MUST load and be interactive within 3 seconds on mobile 3G

#### UI/UX (FR-U-001 to FR-U-009)

- **FR-U-001**: Quiz UI MUST display full-coverage background image with centered quiz container
- **FR-U-002**: Food preferences MUST use visual food icons (64x64px SVG format, fully colored - no monochrome/grayscale) integrated into selections; icons sourced from React Icons or Lucide Icons library with color applied; ALL UI elements MUST be colored (no uncolored icons or graphics)
- **FR-U-003**: Layout MUST show logo and progress "Step X of 20" at top with vertical centering
- **FR-U-004**: Quiz transitions MUST use Framer Motion animations with smooth easing
- **FR-U-005**: Color theme MUST be green & white consistent (primary green: #22c55e or equivalent)
- **FR-U-006**: Validation errors MUST be inline, red-colored, specific (e.g., "Age must be 18-100")
- **FR-U-007**: Loading screen MUST display progress: "Analyzing..." → "Calculating..." → "Selecting..." → "Generating..."
- **FR-U-008**: Success confirmation MUST animate smoothly after PDF email delivery
- **FR-U-009**: Mobile-first responsive design (360px minimum); no horizontal scroll; buttons ≥44px
- **FR-U-010**: Success page MUST display account creation prompt after PDF email confirmation with clear CTA ("Create Account" button) and Skip option; prompt non-intrusive and dismissible
- **FR-U-011**: Background MUST use dark/neutral tone with full-coverage food imagery (per Constitution Principle VIII Keto Creator style)
- **FR-U-012**: Step 20 biometric data collection MUST display lock icon with "100% Private & Confidential" messaging prominently before input fields (privacy reassurance per Constitution)
- **FR-U-013**: Dashboard (optional account) MUST display "Download My Plan" button with PDF availability status and expiration date (X days remaining of 90-day retention)

### Key Entities

- **User**: Stores email (original + normalized per FR-P-010), account creation timestamp, latest meal plan reference for recovery capability
- **Quiz Response**: Temporary storage of 20-step answers, personal traits, biometrics; includes calculated calorie target; deleted within 24 hours after PDF delivery
- **Meal Plan**: Links user to payment, stores meal plan metadata (payment_id, AI model, PDF blob URL, email delivery status, calorie target, refund count, food preference summary as JSONB: {excluded_foods: string[], preferred_proteins: string[], dietary_restrictions: string} derived per FR-A-014), normalized_email (per FR-P-010), 90-day expiration date; biometric data not retained
- **Manual Resolution**: Queue entries for failed operations (missing quiz data, AI validation failures, email delivery failures, manual refunds); tracks issue type, status, SLA deadline, resolution notes; retained 1 year for compliance
- **Magic Link Token**: Secure tokens for PDF recovery without account; tracks token, email (original + normalized), expiration, usage status, IP addresses, user agents; single-use enforcement; 24-hour expiry
- **Email Blacklist**: Stores normalized_email (per FR-P-010) of chargebacked users with 90-day TTL to prevent re-purchase


### Data Retention Policy

| Data Type | Retention Period | Deletion Trigger | Storage Location |
|-----------|------------------|------------------|------------------|
| Quiz responses (full 20-step data) - PAID | 24 hours | After PDF delivery completion | Database (quiz_responses table) |
| Quiz responses (full 20-step data) - UNPAID | 7 days | No payment completed within 7 days of quiz submission | Database (quiz_responses table) |
| Biometric data (age, weight, height) | 24 hours | After PDF delivery completion | Database (quiz_responses table) |
| Food preference summary | 90 days | Auto-cleanup with meal plan record | Database (meal_plans.preferences_summary JSONB) |
| Meal plan metadata (calorie target, generation date, payment ID, AI model) | 90 days | Auto-cleanup job | Database (meal_plans table) |
| PDF file (blob) | 90 days + 24 hour grace period (total 91 days) | Auto-cleanup job | Vercel Blob storage |
| User account data (email, created_at) | Indefinite (until user deletion request) | User-initiated or GDPR request | Database (users table) |
| Manual resolution queue entries | 1 year | Auto-cleanup job | Database (manual_resolution table) |
| Magic link tokens | 24 hours (token expiry) | Auto-cleanup job | Database (magic_link_tokens table) |

**Deletion Implementation Notes:**
- Quiz responses (paid): Deleted via scheduled job running every 6 hours, deleting records where `pdf_delivered_at < NOW() - INTERVAL '24 hours'`
- Quiz responses (unpaid): Deleted via scheduled job running daily, deleting records where `created_at < NOW() - INTERVAL '7 days'` AND `payment_id IS NULL`
- PDF retention (90 days + 24h grace): PDFs deleted via scheduled job running daily at 00:00 UTC, deleting blobs where `created_at < NOW() - INTERVAL '91 days'`; user can access PDF anytime on day 90; deletion occurs only after day 91 begins in UTC
- 90-day retention (meal plan metadata, preference summary): Scheduled daily job deletes records where `created_at < NOW() - INTERVAL '90 days'`
- Manual resolution queue: Deleted via scheduled job running monthly, deleting records where `created_at < NOW() - INTERVAL '1 year'`
- Magic link tokens: Deleted via scheduled job running daily, deleting records where `expires_at < NOW()`
- All deletions logged for compliance audit trail
---

## Success Criteria

- **SC-001**: Quiz completion rate >70% (users who start complete all 20 steps)
- **SC-002**: Payment success rate >95% (quizzes reaching payment result in successful transaction)
- **SC-003**: PDF delivery success >98% (successful payments result in email delivery within 90 seconds)
- **SC-004**: AI quality: 9/10 sample 30-day plans meet keto/variety/practicality criteria (manual review)
- **SC-005**: Keto compliance: 100% pass automated validation (<30g net carbs any day)
- **SC-006**: Email delivery rate >99% (Resend monitoring); <1% bounce/spam
- **SC-007**: PDF recovery success >90% (users requesting recovery via magic link/dashboard succeed within 24h)
- **SC-008**: System uptime >99.5% (Vercel + Sentry monitoring)
- **SC-009**: Performance p95: full journey <90s, AI <20s, PDF <20s, queries <500ms
- **SC-010**: Mobile UX: quiz completion <5 minutes on 3G; no horizontal scroll; all tests pass
- **SC-011**: Security: zero breaches; all health data deleted after PDF delivery; HTTPS everywhere
- **SC-012**: Cost efficiency: stay within free tiers (Vercel Blob 5GB, Resend 100 emails/day) or justify in ADR

---

## Assumptions

1. **User Email Validity**: All user-provided emails are valid and actively monitored; invalid emails detected during sending are retried via Resend with failure logging.

2. **AI API Availability**: Gemini/OpenAI APIs are >99% available during MVP; if outage occurs >1 hour, recovery emails sent to users with one-time regeneration links.

3. **Paddle Payment Integration**: Paddle webhooks verified via HMAC-SHA256 signature; webhook secret stored securely in environment variables; failed verification logged and blocked; no webhook tampering risk when properly verified.

4. **Blob Storage Availability**: Vercel Blob is >99.5% available; PDFs can be reliably stored and retrieved for 90 days.

5. **User Device Capabilities**: Users access quiz on modern browsers (Chrome, Safari, Firefox, Edge) with JavaScript enabled; no support for IE11 or older browsers.

6. **Mifflin-St Jeor Formula Accuracy**: Mifflin-St Jeor formula provides accurate BMR estimates for healthy adults 18-80 years old; no medical validation required (not a medical device).

7. **Keto Diet Safety**: Users are assumed to be responsible for consulting healthcare providers; system enforces keto ratios but does not provide medical advice.

8. **Payment Currency**: MVP supports single currency (USD assumed); multi-currency support deferred to post-MVP phase.

9. **GDPR Compliance**: System assumes EU/non-EU data processing agreements are handled separately; user data deletion requests honored within 30 days.

10. **Time Zone**: System assumes all timestamps stored in UTC; user-facing dates displayed based on browser locale or timezone selector (post-MVP).

11. **PDF Retention**: Users expected to download PDF within 90 days; system not responsible for data recovery beyond 90-day window.

12. **Food Database**: AI model (Gemini/OpenAI) has sufficient knowledge of keto-friendly foods; system does not maintain proprietary food/recipe database.

---

## Dependencies

### Internal Dependencies
- **Constitution** (Principles I-X): All product rules, tech stack, and security requirements defined
- **Project Setup**: GitHub repository configured, Neon DB provisioned, Vercel (frontend) + Render (backend) hosting active

### External Service Dependencies
- **Paddle**: Payment processing, webhook notifications, PCI compliance, transaction management
- **Gemini API / OpenAI API**: AI meal plan generation via OpenAI Agents SDK; Gemini (dev/testing) accessed via AsyncOpenAI client with custom base_url; OpenAI (production) via standard AsyncOpenAI client; model selection based on environment
- **Resend**: Transactional email service with PDF attachment support
- **Vercel Blob**: Blob storage for PDF files with signed URL generation (5GB free tier)
- **Neon DB**: Serverless Postgres for user data, quiz responses, meal plans
- **Vercel**: Frontend hosting (Next.js), Blob storage integration
- **Render**: Backend hosting (FastAPI with Uvicorn), cron job support for cleanup tasks

### Technology Stack Dependencies
- **Frontend**: Next.js, React, TypeScript, React Hook Form, Zod, Tailwind CSS, Framer Motion, React Icons/Lucide
- **Backend**: FastAPI, Pydantic, Uvicorn, Python 3.11+, OpenAI Agents SDK (pip install "openai-agents>=0.1.0,<1.0.0" - pinned to prevent breaking changes)
- **Database ORM**: SQLAlchemy (Python) for database schema and migrations
- **PDF Generation**: ReportLab (Python library for programmatic PDF generation with precise layout control)
- **Caching & Locks**: Redis (distributed locks for concurrent payment prevention per FR-P-007, rate limiting for downloads per FR-R-005 and recovery requests per FR-E-007)
- **Observability**: Sentry (error tracking with email alerts to project owner), Vercel Analytics (performance monitoring and cost dashboards); alerts configured for: error rate >5%, payment failures, storage >80% of free tier, AI API failures >2 consecutive, manual resolution queue SLA breaches

### Data Flow Dependencies
- Quiz responses → Payment webhook → AI generation → PDF creation → Blob storage + Email delivery → User recovery options

---

## Out of Scope

1. **Medical Claims & Advice**: System does NOT provide medical advice, diagnosis, or treatment recommendations; users responsible for consulting healthcare providers before starting keto diet.

2. **Nutritionist Services**: No licensed nutritionist review, personalized coaching, or one-on-one consultation services included.

3. **Meal Plan Regeneration & Customization**: Users receive one AI-generated plan per purchase; no regeneration, editing, or recipe swapping in MVP; customization features deferred to post-MVP based on user feedback.

4. **Multi-Language Support**: MVP supports English only; multi-language interface, content translation deferred to post-MVP.

5. **Multi-Currency Payments**: MVP supports USD only; EUR, GBP, other currency support deferred to Phase 2.

6. **Meal Prep Scheduling & Delivery**: System generates meal plans but does not schedule meal prep reminders, grocery delivery integration, or meal kit services.

7. **Fitness Tracking Integration**: No integration with Apple Health, Fitbit, Garmin, or other fitness trackers; biometrics collected manually via quiz only.

8. **Recipe Video Tutorials**: Meal plan includes written recipes and text instructions only; video cooking tutorials deferred.

9. **Subscription & Recurring Billing**: MVP is one-time purchase model; subscription model and recurring payments deferred to post-MVP.

10. **User Community Features**: No user forums, social sharing, leaderboards, or community interaction features; product is individual user focused.

11. **Admin Dashboard & Customer Support Tools**: No admin portal for customer support team; support handled via email recovery links and FAQ.

12. **A/B Testing & Experimentation Framework**: No built-in experimentation platform; one-time product design for MVP, post-MVP testing tools deferred.

13. **Food Allergy Database Integration**: System relies on user-provided allergy information via Step 17 free text field; no external allergy DB or certification database.

---

## Validation & Acceptance

### Spec Validation Checklist
- [ ] All 20 quiz steps clearly defined (Constitution Principle I)
- [ ] Mifflin-St Jeor calorie calculation formula specified (Constitution Principle X, FR-C-001)
- [ ] Paddle payment integration requirements clear (Constitution Principle II)
- [ ] AI generation constraints documented (Constitution Principles IV-V)
- [ ] PDF storage and recovery flow specified (Constitution Principles II-III)
- [ ] Privacy & data minimization requirements clear (Constitution Principle III)
- [ ] Performance targets defined (Constitution Principle IX)
- [ ] Security & type safety requirements stated (Constitution Principle VII)
- [ ] UI/UX design patterns from Keto Creator specified (Constitution Principle VIII)
- [ ] All 9 edge cases considered and handled
- [ ] 5 user stories with acceptance scenarios defined
- [ ] 12 success criteria measurable and testable
- [ ] 11 assumptions documented
- [ ] Dependencies listed and verified
- [ ] Out of scope items clearly excluded

### Acceptance Test Cases (Manual Testing Priority)
1. **Quiz Flow**: Complete all 20 steps, verify data preservation on back navigation, validate form errors
2. **Payment Integration**: Submit quiz with valid data, complete Paddle payment, verify webhook triggers meal plan generation
3. **AI Generation**: Verify meal plan generated within 20 seconds, validate keto compliance (<30g carbs/day), verify no recipe repetition
4. **PDF Delivery**: Verify PDF email sent with attachment within 90 seconds, blob URL stored in database, recovery link functional
5. **Food Preferences Enforcement**: Generate multiple plans with different food preferences, verify AI respects user dislikes and includes preferred foods
6. **Edge Case - AI Failure**: Simulate AI API timeout, verify retry logic and recovery email with regeneration link sent
7. **Edge Case - Webhook Duplicate**: Send duplicate payment webhook, verify idempotent handling (no double email)
8. **PDF Recovery**: Use magic link and account dashboard to re-download PDF, verify access control and expiration

---

## Next Steps

1. **Review & Clarify** (Stakeholder): Confirm spec requirements; resolve any ambiguities (target: 0 blocking issues)
2. **Create Architecture Plan** (Team): Run `/sp.plan` to generate design decisions and ADR recommendations
3. **Break into Tasks** (Dev): Run `/sp.tasks` to create testable implementation tasks with dependencies
4. **Implement** (Developer): Execute task list with Constitution guardrails; log progress in Prompt History Records
5. **Manual Testing** (QA): Test all 20 quiz steps, payment flow, AI quality samples, PDF delivery
6. **Launch & Monitor** (DevOps): Deploy to production; verify monitoring alerts configured; announce MVP

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-12-22 | Initial specification: 5 user stories, 9 edge cases, 54 FRs (quiz, calorie, payment, AI, PDF, email, recovery, performance, UI/UX), 3 entities, 12 success criteria, 11 assumptions | AI Assistant |
| 1.1.0 | 2025-12-29 | Security audit & loophole fixes: 18 clarifications added, 10 FRs amended (FR-P-002, FR-P-003, FR-P-007, FR-P-008, FR-P-009, FR-R-001, FR-R-002, FR-R-005, FR-E-005, FR-A-007, FR-A-015, FR-C-004, FR-Q-004, FR-Q-009, FR-Q-017, FR-A-014), 13 new FRs added (FR-P-010 email normalization, FR-M-001 to FR-M-006 manual resolution, FR-E-007 public recovery, FR-P-011 refund abuse prevention, FR-P-012 refund compatibility); 3 new entities (manual resolution, magic link tokens, email blacklist); Redis added to tech stack; data retention policy updated; fixes: email verification bypass, blacklist bypass, concurrent purchase race condition, magic link security, account email mismatch, AI validation retry limits, rate limiting | AI Assistant (Claude Sonnet 4.5) |
| 1.2.0 | 2025-12-29 | Hybrid authentication architecture (revenue-optimized): 1 new FR added (FR-Q-020 mid-quiz save progress prompt), 4 FRs amended (FR-Q-009 hybrid persistence, FR-Q-011 incremental saves for auth users, FR-Q-019 auth-aware email verification, FR-R-001 three account creation touchpoints); changes: quiz starts without auth (low friction), optional account creation at Step 10 for cross-device sync, authenticated users get incremental DB saves and skip email verification, unauthenticated users continue with localStorage flow; balances conversion optimization with progressive engagement | AI Assistant (Claude Sonnet 4.5) |
| 1.3.0 | 2026-01-01 | Specification gap resolution: 5 clarifications added addressing identified gaps; 5 FRs amended (FR-M-005 admin authentication, FR-D-005 blob storage, FR-D-006 blob path storage, FR-R-003 on-demand signed URLs, FR-E-002 download endpoint, FR-Q-019 verification validity window); decisions: (1) Admin dashboard uses API key + IP whitelist auth, (2) Generate fresh Vercel Blob signed URLs on-demand (not pre-generated) to prevent URL expiry mismatch during 90-day retention, (3) Gmail-only email normalization sufficient for MVP (accept non-Gmail bypass risk), (4) Email verification valid 24h after code entry (allows Paddle modal abandonment recovery), (5) Accept Redis lock race condition as acceptable MVP risk (narrow exploit window, two-layer protection sufficient) | AI Assistant (Claude Sonnet 4.5) |
