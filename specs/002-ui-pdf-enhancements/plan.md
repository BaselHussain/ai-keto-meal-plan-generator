# Implementation Plan: UI & PDF Enhancements

**Branch**: `002-ui-pdf-enhancements` | **Date**: 2026-02-27 | **Spec**: [specs/002-ui-pdf-enhancements/spec.md](specs/002-ui-pdf-enhancements/spec.md)
**Input**: Feature specification from `/specs/002-ui-pdf-enhancements/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implementation of UI & PDF Enhancements featuring homepage redesign matching image.png exactly, PDF generation improvements (removing blank pages and adding personalized food suggestions), quiz route migration to /quiz, professional footer with legal links, and blog page with educational content. The solution involves frontend changes using Next.js App Router with shadcn/ui components, backend PDF generation improvements using ReportLab, and static content pages.

## Technical Context

**Language/Version**: TypeScript 5.x, Python 3.11+
**Primary Dependencies**: Next.js 14.x (App Router), React, FastAPI, ReportLab, shadcn/ui, Tailwind CSS, React Hook Form, Zod
**Storage**: PostgreSQL (Neon DB) for existing data, Vercel Blob for PDF storage
**Testing**: Jest/React Testing Library for frontend, pytest for backend
**Target Platform**: Web application (Next.js frontend + FastAPI backend)
**Project Type**: Web application (frontend + backend)
**Performance Goals**: <3 seconds page load (mobile 3G), PDF generation <20 seconds
**Constraints**: Responsive design (mobile-first), accessibility compliance (WCAG 2.1 AA), PDF file size 400-600KB
**Scale/Scope**: Existing user base, 30-day meal plan PDFs with food suggestions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution Check Results**:
- ✅ Principle I (Personalization): PDF food suggestions will be dynamically generated based on user quiz responses
- ✅ Principle III (Privacy-First): No additional data stored; PDF enhancements use existing quiz data
- ✅ Principle IV (Keto Compliance): Food suggestions will follow keto guidelines
- ✅ Principle VII (Type Safety): TypeScript and Zod validation will be used for new components
- ✅ Principle VIII (UX Excellence): Homepage redesign will follow mobile-first responsive design
- ✅ Principle X (Accurate Calorie Estimation): Food suggestions will incorporate user calorie targets

**Gates Status**: PASS - All constitution principles are satisfied by the proposed implementation

## Project Structure

### Documentation (this feature)

```text
specs/002-ui-pdf-enhancements/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
│   └── api-contracts.md # API contracts for new endpoints
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
frontend/
├── app/
│   ├── page.tsx                 # New landing page from image.png
│   ├── quiz/
│   │   └── page.tsx             # Moved quiz functionality
│   ├── privacy-policy/
│   │   └── page.tsx             # Static privacy policy page
│   ├── terms/
│   │   └── page.tsx             # Static terms page
│   ├── returns-policy/
│   │   └── page.tsx             # Static returns policy page
│   └── blog/
│       └── page.tsx             # Blog page with content + mistakes section
├── components/
│   └── Footer.tsx               # New footer component with links
├── lib/
│   └── utils.ts                 # Utility functions
└── styles/
    └── globals.css              # Global styles

backend/
├── pdf/
│   ├── generator.py             # PDF fixes + food suggestions (was .js in req)
│   ├── templates/               # PDF templates
│   └── models/                  # PDF-related models
└── api/
    └── endpoints/               # API endpoints

tests/
├── frontend/
│   ├── __tests__/
│   └── fixtures/
└── backend/
    ├── __tests__/
    └── fixtures/
```

**Structure Decision**: Web application structure selected as this is a frontend/UI + backend feature requiring both Next.js pages/components and backend PDF generation logic. The existing project already follows this structure with frontend and backend components.

## Phase 0: Research & Analysis
- [x] Technical requirements analysis
- [x] Implementation approach evaluation
- [x] Technology compatibility verification
- [x] Research.md created with findings and decisions

## Phase 1: Design & Architecture
- [x] Data model design completed (data-model.md)
- [x] API contracts defined (contracts/api-contracts.md)
- [x] Quickstart guide created (quickstart.md)
- [x] Architecture patterns validated
- [x] Project structure finalized

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations identified. All implementation approaches align with existing project principles.

## Dependencies & Integration Points

- **Frontend**: Next.js 14 App Router, Tailwind CSS, shadcn/ui components
- **Backend**: FastAPI endpoints, ReportLab PDF generation
- **PDF Generation**: Enhanced generator.py with blank page fixes and food suggestions
- **Content**: Integration with Custom keto diet meal plan change final.md file
- **UI Components**: shadcn/ui for consistent design system
