<!--
Sync Impact Report:
- Version change: 1.0.0 → 1.3.1
- Improved testability: replaced vague quality terms with measurable criteria in Principle V
- Added new Principle IX: Performance and Monitoring with SLOs and observability requirements
- Added new Principle X: Accurate Calorie Estimation with Mifflin-St Jeor formula and safety limits
- MAJOR UPDATE: Principle I now specifies exact 20-step quiz structure inspired by Keto Creator (granular food preferences, behavioral patterns)
- MAJOR UPDATE: Principle VIII now mandates UI/UX patterns inspired by Keto Creator (icon-based selections, progressive disclosure, privacy messaging, loading screens)
- Updated Development Workflow: adapted for solo developer reality with practical quality gates
- Clarified meal plan scope: 30-day plans (not 7-day), adjusted performance targets accordingly
- Hybrid delivery: PDF stored in blob storage (Vercel Blob/Cloudinary) + sent as email attachment for user recovery
- Added re-download capability: users can recover lost PDFs via account/magic link
- PDF retention: 90 days minimum
- Templates requiring updates: None (clarifications and expansions only)
- Follow-up TODOs: Implement 20-step quiz UI with icons, BMR/calorie calculation logic, food preference filtering in AI prompts, monitoring dashboard, cost alerts
-->

# AI-Powered Personalized Keto Meal Plan Generator Constitution

## Core Principles

### I. Personalization Through AI-Driven Insights

The system MUST generate personalized 30-day keto meal plans based on accurate user inputs collected through a comprehensive 20-step quiz. Every recommendation MUST be tailored to individual user parameters collected through granular food preferences, behavioral patterns, biometric data, and personal goals.

**Rationale**: Generic meal plans fail to address individual needs and reduce user engagement. Detailed food-level preferences enable precise personalization and increase likelihood of user success with keto adherence.

**Quiz Structure (20 Steps - Inspired by Keto Creator):**

**Steps 1-2: Personal Profile**
1. Gender selection (Female/Male)
2. Activity level (5-tier: Sedentary, Lightly Active, Moderately Active, Very Active, Super Active)

**Steps 3-17: Granular Food Preferences**
3. Meat preferences (beef, lamb, chicken, pork, turkey, or none)
4. Fish varieties (tuna, salmon, mackerel, cod, pollock, or none)
5. Vegetables (avocado, asparagus, bell pepper, zucchini, celery, mushrooms)
6. Cruciferous vegetables (brussels sprouts, kale, broccoli, cauliflower)
7. Leafy greens (lettuce, spinach, arugula, cilantro, iceberg, napa cabbage)
8. Legumes preferences
9. Shellfish (clams, crustaceans, or none)
10. Fruits preferences
11. Berries preferences
12. Grains preferences
13. Other carbs preferences
14. Cooking fats (coconut oil, olive oil, peanut butter, butter, lard, vegetable oil)
15. Beverages (water, coffee, tea, soda, smoothies, juices, milk, wine, beer, spirits)
16. Dairy products (Greek yogurt, cheese, sour cream, cottage cheese, or none)
17. Additional dietary restrictions or allergies (free text)

**Steps 18-19: Behavioral Patterns**
18. Eating frequency (1 time a day, 2 times a day, 3 times a day, 4 or more times a day)
19. Personal traits checkboxes:
    - "I often feel tired when I wake up"
    - "I have frequent cravings"
    - "I prefer salty foods"
    - "I prefer sweet foods"
    - "I struggle with appetite control"

**Step 20: Biometric Data (with "100% Private & Confidential" messaging)**
- Age
- Weight (kg or lbs with unit selector)
- Height (cm or ft/in with unit selector)
- Goal (weight loss, muscle gain, maintenance)

**Non-negotiable rules**:
- 20-step quiz structure MUST be followed exactly as specified
- All user inputs MUST be validated before AI processing (React Hook Form + Zod)
- AI prompts MUST incorporate all collected parameters (food preferences, behavioral traits, biometrics)
- Generated plans MUST reflect user-specific food preferences and exclude disliked items
- No default or template-based meal plans; every plan MUST be AI-generated per user
- Biometric data collection MUST display privacy reassurance ("100% Private & Confidential" with lock icon)

### II. Full Automation from Quiz to Delivery

The entire user journey from quiz submission to receiving a personalized PDF meal plan via email MUST be fully automated with zero manual intervention. The system MUST handle quiz submission, payment processing, AI generation, PDF creation, blob storage, and email delivery with attachment as a seamless automated workflow.

**Rationale**: Manual steps introduce delays, errors, and scaling bottlenecks. Full automation ensures consistent user experience and enables cost-effective scaling. PDF backup storage enables user recovery if email is lost.

**Non-negotiable rules**:
- Quiz → Payment → AI Generation → PDF → Blob Storage → Email Attachment MUST execute as automated pipeline
- Webhook handlers MUST be idempotent to handle retries safely
- Failed steps MUST trigger automated retries with exponential backoff
- All state transitions MUST be logged for debugging and monitoring
- PDF stored in blob storage with URL saved to database for re-download capability

### III. Privacy-First Data Management

User data storage MUST be minimized to only essential information required for service delivery. Personal health information and meal plan details MUST NOT be stored longer than necessary. Payment details MUST be handled exclusively by Paddle (PCI-compliant processor).

**Rationale**: Privacy builds trust and reduces regulatory/legal risk. Minimal data storage reduces attack surface and compliance burden.

**Non-negotiable rules**:
- Store only: user email, quiz responses (temporary), payment status, PDF blob URL
- PDF stored in blob storage (Vercel Blob/Cloudinary) AND sent as email attachment
- PDF retention: 90 days minimum (allows users to re-download if lost)
- No credit card data stored; Paddle handles all payment details
- Quiz responses deleted after PDF generation and email delivery (24 hours max)
- HTTPS only for all communications
- Environment variables for all API keys and secrets

### IV. Keto Compliance Guarantee

All AI-generated meal plans MUST strictly adhere to ketogenic diet standards: <30g net carbs per day, appropriate protein intake, high healthy fat content. Macronutrient calculations MUST be accurate and displayed clearly for each meal and daily totals.

**Rationale**: Users trust the product to deliver medically-sound keto meal plans. Non-compliant plans damage credibility and user health outcomes.

**Non-negotiable rules**:
- AI prompts MUST enforce <30g net carbs/day constraint
- Every meal MUST include macro breakdown (carbs, protein, fat, calories)
- Daily totals MUST be calculated and verified
- Recipes MUST use keto-approved ingredients only
- AI outputs MUST be validated for keto compliance before PDF generation

### V. Reliability and Quality Standards

The system MUST deliver consistent, high-quality AI-generated meal plans across all users. AI prompt engineering MUST ensure variety, nutritional balance, practical recipes, and motivational content. Error handling MUST gracefully manage AI API failures, payment webhook issues, and email delivery problems.

**Rationale**: Inconsistent outputs erode trust. Reliability is critical for a paid product. Measurable quality criteria enable objective validation.

**Measurable Quality Criteria**:
- AI response time: <20 seconds for 30-day meal plan generation (p95)
- Meal variety: No recipe repeated within same 30-day plan
- Nutritional balance: Every day meets keto ratios (65-75% fat, 20-30% protein, 5-10% carbs)
- Recipe practicality: ≤10 ingredients per meal, ≤30 minutes prep time
- AI validation pass rate: >95% of generated plans pass keto compliance checks

**Testing Acceptance Criteria**:
- AI prompt quality: Manual review of 10 sample 30-day outputs MUST show 9/10 meet criteria above
- Keto compliance: Automated validation MUST reject any plan with ANY day >30g net carbs
- Variety score: Algorithm MUST check for duplicate recipes within 30-day plan

**Non-negotiable rules**:
- Structured, reusable AI prompts with version control
- AI prompt templates MUST include: keto compliance rules, variety requirements, tone guidelines
- Retry logic for all external API calls (AI, email, storage)
- Fallback mechanisms for temporary service failures
- Logging of AI request metadata (not full responses) for quality monitoring

### VI. Cost-Effective Development

Development MUST prioritize free-tier and cost-effective services to minimize operational costs during MVP and early growth phases. Technology choices MUST balance functionality with budget constraints.

**Rationale**: Bootstrapped SaaS requires lean operations. Premature scaling costs kill early-stage products.

**Non-negotiable rules**:
- Use free tiers where available: Neon DB (Postgres), Vercel (hosting + Blob storage 5GB free), Resend (email), Cloudinary (25GB free alternative)
- Gemini API for testing/development; OpenAI API for production (cost vs. quality tradeoff)
- PDF stored in blob storage (free tier first: Vercel Blob 5GB or Cloudinary 25GB)
- Monitor API usage and storage to stay within free/low-cost limits
- Justify any paid service with clear ROI or critical functionality

### VII. Type Safety and Code Quality

All code MUST be type-safe, modular, well-documented, and maintainable. Frontend validation (Zod), backend validation (Pydantic), and clear API contracts MUST prevent runtime errors and data quality issues.

**Rationale**: Type safety catches bugs early, reduces debugging time, and improves long-term maintainability.

**Non-negotiable rules**:
- TypeScript for all frontend code (Next.js)
- Pydantic models for all backend data structures (FastAPI)
- Zod schemas for all form validation (React Hook Form)
- API contracts MUST be documented (OpenAPI/FastAPI auto-docs)
- Error handling MUST be explicit and logged
- Code reviews MUST verify type safety before merge

### VIII. User Experience Excellence

UI/UX MUST be clean, responsive (mobile-first), and intuitive, directly inspired by Keto Creator's proven design patterns. The 20-step quiz flow MUST guide users smoothly through all questions with clear validation feedback. The green & white theme MUST be consistent across all pages. Loading states, error messages, and success confirmations MUST be clear and user-friendly. Users MUST be able to re-download their PDF if lost.

**Rationale**: User experience directly impacts conversion rates and customer satisfaction. Keto Creator's UX patterns have proven effectiveness in the keto meal plan market. Poor UX increases abandonment and support costs. PDF re-download capability reduces support burden.

**Design Inspiration: Keto Creator UX Patterns**
- **Page layout**: Full-coverage background image with centered quiz container (dark background with food imagery)
- **Quiz positioning**: Vertically centered on page with food/dish images integrated into selections
- Progressive disclosure: 20-step multi-step form reduces cognitive load (one question visible at a time)
- Icon-based food selections: Visual choices with 64x64px food icons integrated into quiz (not decorative, but functional)
- Privacy reassurance: Lock icon and "100% Private & Confidential" messaging before biometric data (Step 20)
- Back/Next navigation: Users can correct previous answers
- Loading screen: Post-payment shows "Analyzing data... Calculating nutritional profile... Selecting recipes... Generating your 30-day plan..."
- Step progress indicator: Show "Step X of 20" throughout quiz at top with logo
- Clean, focused design with emphasis on user interaction (not cluttered decorative elements)

**Non-negotiable rules**:
- **Layout**: Full-coverage background image with centered quiz container (Keto Creator style)
- **Visual hierarchy**: Logo and progress at top, quiz centered, food icons integrated into selections
- Mobile-first responsive design (test on mobile devices, down to 360px width)
- 20-step quiz with progress indicator ("Step X of 20") at top of page
- Icon-based selections for food preferences (64x64px food icons, visual choices not text-only lists)
- Food images functionally integrated into quiz selections (not decorative corner elements)
- Inline validation with clear error messages (React Hook Form + Zod)
- Privacy lock icon displayed before biometric data collection (Step 20)
- Green & white color theme consistently applied (inspired by Keto Creator's clean aesthetic)
- Dark/neutral background with full-coverage background image
- Back/Next navigation buttons on every quiz step
- Loading screen with progress messages: "Analyzing data..." → "Calculating nutritional profile..." → "Selecting recipes..." → "Generating your 30-day plan..."
- User-friendly error messages (no technical jargon)
- Success confirmation after payment and email delivery
- User account/dashboard with "Download My Plan" button for PDF recovery (optional login or magic link via email)
- Quiz completion MUST feel seamless and professional (benchmark: Keto Creator experience)

### IX. Performance and Monitoring

The system MUST meet defined performance targets and provide observability into health, costs, and user experience. Monitoring MUST enable proactive detection of issues before users are impacted. Cost tracking MUST prevent unexpected billing from free-tier overages.

**Rationale**: Performance directly impacts user satisfaction and conversion. Monitoring enables rapid issue detection. Cost awareness prevents budget surprises during MVP phase.

**Performance Requirements**:
- Quiz submission → Email delivery: <90 seconds (p95) - includes 30-day plan generation
- Payment webhook processing: <5 seconds
- PDF generation (30-day plan): <20 seconds
- Database queries: <500ms (p95)
- Frontend page load: <3 seconds (mobile 3G)

**Required Monitoring**:
- Track: API response times, error rates, payment success rate, email delivery rate (with attachments), blob storage usage
- Alert when: Error rate >5%, AI API failures >2 consecutive, email delivery fails, storage approaching 80% of free tier
- Cost monitoring: Alert at 80% of free tier limits (Resend emails, Gemini/OpenAI API, Vercel/Blob storage, Neon DB)
- Dashboard MUST show: daily users, revenue, meal plans generated, error breakdown, storage usage

**Logging Standards**:
- Log levels: ERROR (failures), WARN (retries), INFO (state changes only)
- Do NOT log: user health data, payment details, full AI responses (metadata only)
- Retention: 30 days for debugging, compliance with data minimization principle

**Non-negotiable rules**:
- Response time monitoring for all API endpoints
- Error tracking service integrated (Sentry free tier for error monitoring)
- Cost usage dashboards for all paid/free-tier services (Vercel Analytics dashboard)
- Alerts configured before production launch via Sentry email notifications (sent to project owner email); critical alerts (error rate >5%, payment failures, storage >80%) trigger immediate email notifications

### X. Accurate Calorie Estimation

The system MUST calculate a personalized daily calorie target for each user before generating the meal plan. Calorie estimation MUST be based on the Mifflin-St Jeor formula for BMR, multiplied by activity level, and adjusted according to the user's goal (deficit for weight loss, surplus for muscle gain, neutral for maintenance). Minimum safe limits: never below 1200 kcal for women or 1500 kcal for men.

**Rationale**: Accurate calorie targets ensure safe, effective, and sustainable keto plans tailored to individual metabolism and goals.

**Non-negotiable rules**:
- Use Mifflin-St Jeor equation for BMR calculation (Men: (10 × weight_kg) + (6.25 × height_cm) - (5 × age) + 5; Women: (10 × weight_kg) + (6.25 × height_cm) - (5 × age) - 161)
- Apply standard activity multipliers (Sedentary 1.2, Lightly Active 1.375, Moderately Active 1.55, Very Active 1.725, Super Active 1.9)
- Goal-based adjustment: Weight Loss = -400 kcal deficit, Muscle Gain = +250 kcal surplus, Maintenance = 0 kcal adjustment
- Calorie target MUST be passed to the main AI meal plan prompt
- All calculations MUST be deterministic and reproducible

## Tech Stack Standards

**Frontend**: Next.js (React framework), TypeScript, React Hook Form, Zod (validation), Tailwind CSS (green & white theme inspired by Keto Creator), React Icons or Lucide Icons (for food/activity icons)

**Backend**: FastAPI (Python), Pydantic (data validation), Uvicorn (ASGI server)

**Database**: Neon DB (serverless Postgres) - stores user email, payment status, PDF blob URL

**AI Services**: Gemini API (testing/development), OpenAI API (production)

**Payments**: Paddle (handles all payment processing, PCI compliance)

**PDF Generation**: Python libraries (ReportLab or WeasyPrint for PDF creation)

**File Storage**: Vercel Blob or Cloudinary (PDF storage with 90-day retention minimum)

**Email**: Resend (transactional emails with PDF attachments)

**Hosting**: Vercel (frontend + serverless functions)

**Technology Change Policy**: Any deviation from this stack MUST be documented with justification in an ADR (Architecture Decision Record).

## Security & Privacy Requirements

**Secrets Management**:
- All API keys, database credentials, and secrets MUST be stored in environment variables
- NEVER commit secrets to version control
- Use `.env.local` for local development (gitignored)
- Use Vercel environment variables for production

**Communication Security**:
- HTTPS ONLY for all client-server communication
- API endpoints MUST validate request signatures (Paddle webhooks)
- CORS configured to allow only authorized origins

**Data Protection**:
- Minimal data storage (email, payment status, PDF blob URL only)
- Quiz responses deleted after PDF generation and email delivery (max 24 hours retention)
- PDF stored in blob storage with 90-day retention minimum (user recovery)
- PDF blob URLs MUST be non-guessable (UUID-based or signed URLs)
- No logging of sensitive user data (health info, payment details)

**Compliance**:
- GDPR awareness: data minimization, user data deletion on request
- PCI compliance: handled by Paddle (no card data stored)

## Development Workflow

**Branching Strategy**:
1. Create GitHub repository at project start
2. Default branch: `main` (protected, production-ready code only)
3. Create `development` branch from `main` at start
4. Set `development` as primary working branch (deploy to staging)
5. Feature branches from `development`: `feature/<feature-name>`
6. Pull requests: feature → development → main

**Branch Protection**:
- `main` branch: protected, requires PR approval, no direct commits
- `development` branch: primary integration branch

**Solo Developer Code Quality Process**:
- Self-review checklist MUST be completed before merge (even solo, create PR for documentation):
  - ✓ TypeScript/Pydantic types enforced with no `any` types
  - ✓ Zod validation added for all forms and user inputs
  - ✓ Error handling implemented for all external API calls
  - ✓ Constitution principles verified (keto compliance, privacy, security)
  - ✓ Manual testing completed for affected features
  - ✓ No secrets committed (check `.env` files gitignored)
- Create PR even when solo (serves as documentation and rollback point)
- PR description MUST include: what changed, why, testing performed

**Testing Strategy (MVP-Prioritized)**:

**MUST HAVE (Required for Launch)**:
1. Manual testing of all user-facing features, including all 20 quiz steps
2. Quiz flow validation: Test navigation (back/next), form validation, progress indicator, icon displays
3. AI prompt quality validation: Test 10 sample 30-day generations with varied food preferences, verify 9/10 meet Principle V criteria
4. Food preference enforcement: Verify generated plans exclude user-disliked foods and include preferred foods
5. Payment flow integration test: Complete test purchase end-to-end
6. Keto compliance validation: Automated check for <30g net carbs per day across all 30 days, macro calculations

**SHOULD HAVE (Post-MVP, Pre-Scale)**:
1. Unit tests for critical functions: AI API calls, webhook handlers, email sending
2. Integration tests for payment flow with Paddle sandbox
3. Form validation tests (Zod schema tests)

**NICE TO HAVE (Future Enhancement)**:
1. E2E tests with Playwright for frontend flows
2. Pytest integration tests for full backend pipeline
3. Load testing for performance validation

**Testing Priority**:
- Manual testing first (fast iteration for AI prompts and UI)
- Automated tests for critical paths added incrementally
- E2E test suite deferred until post-MVP (focus on shipping)

**Commit & PR Standards**:
- Descriptive commit messages: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- PRs MUST include: description, testing done, screenshots (if UI changes)
- Self-review with checklist before merge to `development`
- Merge to `main` only after thorough testing on `development` (staging environment)

**Documentation Requirements**:
- README MUST include: project overview, setup instructions, environment variables needed
- API endpoints documented via FastAPI auto-generated docs
- AI prompts versioned and documented in code comments

## Governance

**Constitution Authority**: This constitution supersedes all other development practices and architectural decisions. Any violation MUST be documented and justified in an ADR (Architecture Decision Record).

**Amendment Process**:
1. Proposed changes MUST be discussed and documented
2. Impact assessment MUST identify affected code and templates
3. Migration plan MUST be created for breaking changes
4. Approval required before amendment (document approver)
5. Version number MUST be incremented per semantic versioning

**Compliance Verification**:
- All PRs MUST verify compliance with constitution principles
- Code reviews MUST check for violations (type safety, security, keto compliance)
- Complexity or deviations MUST be justified in PR description or ADR

**Versioning Policy**:
- **MAJOR**: Backward-incompatible changes (principle removal/redefinition)
- **MINOR**: New principle added or significant expansion
- **PATCH**: Clarifications, wording fixes, non-semantic updates

**Version**: 1.3.1 | **Ratified**: 2025-12-21 | **Last Amended**: 2025-12-22
