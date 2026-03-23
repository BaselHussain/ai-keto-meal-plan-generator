# Tasks: UI & PDF Enhancements

**Feature**: UI & PDF Enhancements
**Branch**: `002-ui-pdf-enhancements`
**Created**: 2026-02-27
**Status**: Draft

## Implementation Strategy

This feature implements UI & PDF enhancements with a focus on homepage redesign matching image.png exactly, PDF generation improvements (removing blank pages and adding personalized food suggestions), quiz route migration to /quiz, professional footer with legal links, and blog page with educational content. Each user story is independently testable and delivers value to users.

**MVP Scope**: User Story 1 (Homepage Redesign) - delivers the new homepage design matching image.png to provide immediate visual improvement to users.

---

## Phase 1: Setup
**Goal**: Initialize project structure and install required dependencies

- [X] T001 Set up shadcn/ui components following Next.js App Router integration guide
- [X] T002 Update frontend dependencies to support new UI features (if needed)
- [X] T003 Locate image.png file referenced for homepage design
- [X] T004 Verify backend/ directory structure exists for PDF improvements

## Phase 2: Foundational
**Goal**: Create foundational components and update PDF generation infrastructure

- [X] T005 [P] Install ReportLab and verify PDF generation setup in backend
- [X] T006 [P] Create PDF generator enhancement utilities in backend/pdf/
- [X] T007 [P] Set up reusable UI components for blog and features section using shadcn/ui
- [X] T008 [P] Create shared layout components for consistent site-wide footer implementation

## Phase 3: [US1] Homepage Redesign
**Goal**: Create exact homepage UI from image.png with key features section
**Independent Test**: User can load the homepage and see the exact UI matching image.png with hero banner, proper layout, colors, and styling that matches the design, plus key features section

- [X] T009 [US1] Create homepage layout in frontend/app/page.tsx matching image.png design
- [X] T010 [US1] Implement hero banner section with image, title, and subtitle matching image.png
- [X] T011 [US1] Add key features section with 5-6 bullet points and icons on homepage
- [X] T012 [US1] Ensure homepage is responsive and matches image.png on mobile devices
- [X] T013 [US1] Validate homepage design against image.png for exact match
- [X] T014 [US1] Implement styling to match color scheme and layout from image.png
- [X] T015 [US1] Add any missing navigation links or elements from image.png design
- [X] T016 [US1] Test homepage layout across different screen sizes

## Phase 4: [US2] PDF Generation Improvements
**Goal**: Remove blank second page from generated PDF and add 5 food combination suggestions based on user quiz responses
**Independent Test**: User can complete quiz, generate PDF meal plan, and receive a PDF without blank pages containing 5 personalized food combination suggestions

- [X] T017 [US2] Update backend/pdf/generator.py to remove blank second page issue
- [X] T018 [US2] Implement food suggestions generation based on user quiz responses
- [X] T019 [US2] Add 5 food combination suggestions (breakfast, lunch, dinner) to PDF
- [X] T020 [US2] Ensure food suggestions are personalized based on user preferences
- [X] T021 [US2] Update PDF generation API response to include food_suggestions array
- [X] T022 [US2] Validate keto compliance of generated food suggestions
- [X] T023 [US2] Test PDF generation with various quiz responses to verify suggestions
- [X] T024 [US2] Verify no blank pages appear in generated PDFs
- [X] T025 [US2] Add food suggestions to the meal plan response API

## Phase 5: [US3] Quiz Route Migration
**Goal**: Move quiz functionality to /quiz route for clearer navigation
**Independent Test**: User can navigate to /quiz route and access the complete quiz functionality

- [X] T026 [US3] Move existing quiz component to frontend/app/quiz/page.tsx
- [X] T027 [US3] Update navigation links to point to /quiz route instead of previous location
- [X] T028 [US3] Ensure all quiz functionality works at new /quiz route
- [X] T029 [US3] Update any internal links that reference the old quiz location
- [X] T030 [US3] Test quiz navigation flow from homepage to /quiz route
- [X] T031 [US3] Update any backend API references that may need updating

## Phase 6: [US4] Footer Implementation
**Goal**: Implement professional footer with Privacy Policy, Terms, and Returns Policy links
**Independent Test**: User can see the footer on all pages and click links to access Privacy Policy, Terms, and Returns Policy pages

- [X] T032 [US4] Create reusable Footer component in frontend/components/Footer.tsx
- [X] T033 [US4] Add Privacy Policy, Terms, and Returns Policy links to footer
- [X] T034 [US4] Implement privacy policy page at frontend/app/privacy-policy/page.tsx
- [X] T035 [US4] Implement terms page at frontend/app/terms/page.tsx
- [X] T036 [US4] Implement returns policy page at frontend/app/returns-policy/page.tsx
- [X] T037 [US4] Add placeholder content to legal pages
- [X] T038 [US4] Ensure footer appears consistently across all site pages
- [X] T039 [US4] Test all footer links for proper navigation

## Phase 7: [US5] Blog Page Creation
**Goal**: Create blog page with content from Custom keto diet meal plan change final.md and "Mistakes to avoid in keto meal" section
**Independent Test**: User can navigate to /blog and read content from the specified file plus section about common keto mistakes

- [X] T040 [US5] Create blog page structure at frontend/app/blog/page.tsx
- [X] T041 [US5] Implement content loading from Custom keto diet meal plan change final.md
- [X] T042 [US5] Add "Mistakes to avoid in keto meal" section with 5-10 common mistakes
- [X] T043 [US5] Format blog content with appropriate styling and layout
- [X] T044 [US5] Implement content loading API endpoint for blog content
- [X] T045 [US5] Add responsive design elements to blog page
- [X] T046 [US5] Generate 5-10 relevant keto mistakes if content file is not accessible
- [X] T047 [US5] Ensure blog page is mobile-friendly and well-formatted

## Phase 8: [US6] Key Features Section
**Goal**: Add key features section on homepage using content from spec 1
**Independent Test**: User can see key features section on homepage with information taken from spec 1

- [X] T048 [US6] Locate content for key features section from spec 1
- [X] T049 [US6] Implement key features UI components with icons using shadcn/ui
- [X] T050 [US6] Add key features section to homepage layout
- [X] T051 [US6] Ensure key features are prominently displayed on homepage
- [X] T052 [US6] Validate that the key features match the content from spec 1

## Phase 9: Polish & Cross-Cutting Concerns
**Goal**: Final integration, testing, and quality assurance across all features

- [X] T053 Update all navigation to ensure consistency across new routes
- [X] T054 Add responsive design improvements to all new pages
- [X] T055 Ensure all UI elements follow mobile-first responsive design principles
- [X] T056 Add accessibility improvements to new components following WCAG 2.1 AA
- [X] T057 Run comprehensive tests across all new functionality
- [X] T058 Update any documentation to reflect new routes and features
- [X] T059 Verify all features maintain existing functionality (no breaking changes)
- [X] T060 Performance test homepage load time and PDF generation time
- [X] T061 Validate that all constitution principles are satisfied (personalization, privacy, keto compliance, etc.)
- [X] T062 Final user acceptance testing of all new features

---

## Dependencies & Execution Order

**User Story Completion Order**: US1 → US2 → US3 → US4 → US5 → US6

**Dependencies**:
- US1 (Homepage) can be implemented independently
- US2 (PDF) can be implemented independently but builds on foundational setup
- US3 (Quiz) should come after any potential navigation changes from US1
- US4 (Footer) implementation should happen after foundational layout components
- US5 (Blog) can be implemented independently
- US6 (Key Features) depends on US1 (homepage implementation)

## Parallel Execution Opportunities

**Within Each User Story**:
- US1: Layout implementation can happen in parallel with styling work
- US2: Backend PDF changes can happen in parallel with API response updates
- US4: Creating individual static pages can happen in parallel
- US5: Content API implementation can happen in parallel with frontend page design

**Across User Stories** (if resources allow):
- US2 (PDF) and US4 (Footer) can be developed simultaneously
- US5 (Blog) and US6 (Key Features) can be developed simultaneously