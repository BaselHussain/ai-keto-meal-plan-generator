# Quickstart Guide: UI & PDF Enhancements

**Feature**: UI & PDF Enhancements
**Date**: 2026-02-27
**Author**: Claude

## Setup and Development Environment

### Pre-requisites
- Node.js 18+ and npm/yarn/bun
- Python 3.11+
- PostgreSQL (or Neon DB connection)
- Redis (for rate limiting)
- Environment variables configured (see .env.example)

### Installation Steps

1. **Install frontend dependencies**:
   ```bash
   cd frontend
   npm install  # or yarn install or bun install
   ```

2. **Install backend dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Setup database**:
   ```bash
   cd backend
   alembic upgrade head
   ```

4. **Run development servers**:
   ```bash
   # Frontend
   cd frontend
   npm run dev  # Starts Next.js dev server on port 3000

   # Backend
   cd backend
   uvicorn main:app --reload --port 8000
   ```

## Running the Application

### Development Mode
```bash
# Terminal 1 - Frontend
cd frontend && npm run dev

# Terminal 2 - Backend
cd backend && uvicorn main:app --reload --port 8000
```

### Production Mode
```bash
# Build frontend
cd frontend && npm run build

# Run backend
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000
```

## Key Features Implementation

### 1. Homepage Redesign (matches image.png)
- Located at `frontend/app/page.tsx`
- Uses exact design from image.png (hero banner, layout, colors)
- Includes key features section with 5-6 bullet points and icons

### 2. PDF Generation Improvements
- Located at `backend/pdf/generator.py`
- Removes blank second page issue
- Adds 5 personalized food combination suggestions based on quiz responses
- Maintains existing 30-day meal plan structure

### 3. Quiz Route Migration
- Moved from previous location to `frontend/app/quiz/page.tsx`
- All navigation links updated to point to /quiz route

### 4. Footer Component
- New component at `frontend/components/Footer.tsx`
- Includes Privacy Policy, Terms, and Returns Policy links
- Applied site-wide via layout files

### 5. Static Legal Pages
- `frontend/app/privacy-policy/page.tsx`
- `frontend/app/terms/page.tsx`
- `frontend/app/returns-policy/page.tsx`

### 6. Blog Page
- Located at `frontend/app/blog/page.tsx`
- Loads content from Custom keto diet meal plan change final.md
- Includes "Mistakes to avoid in keto meal" section (5-10 points)

## Testing the Features

### Homepage Design
1. Navigate to `http://localhost:3000/`
2. Verify layout, colors, hero banner match image.png exactly
3. Check responsive design on mobile

### PDF Generation
1. Complete quiz flow
2. Generate meal plan PDF
3. Verify no blank pages
4. Check that 5 food suggestions are present and personalized

### New Routes
1. `/quiz` - verify quiz functionality works
2. `/blog` - verify content loads and mistakes section is present
3. Legal pages - verify links in footer work

### Component Testing
```bash
# Frontend tests
cd frontend && npm run test

# Backend tests
cd backend && pytest
```

## Key Libraries and Tools

- **shadcn/ui**: Component library for new UI elements
- **ReportLab**: PDF generation and manipulation
- **Tailwind CSS**: Styling and responsive design
- **React Hook Form + Zod**: Form validation
- **Next.js 14 App Router**: Page routing and structure

## Troubleshooting

### Common Issues
1. **Homepage doesn't match image.png**: Check CSS classes and layout components
2. **Blank PDF pages still present**: Verify ReportLab canvas configuration
3. **Food suggestions not personalized**: Ensure quiz response data is passed to PDF generation
4. **Blog content not loading**: Verify path to Custom keto diet meal plan change final.md file

### Development Tips
- Use Next.js hot reload for real-time UI updates
- Check browser console for frontend errors
- Check backend logs for API errors
- Use shadcn/ui documentation for component customization