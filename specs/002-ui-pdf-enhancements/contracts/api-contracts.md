# API Contracts: UI & PDF Enhancements

**Feature**: UI & PDF Enhancements
**Date**: 2026-02-27
**Author**: Claude

## Overview

API contracts for UI & PDF Enhancement features including PDF generation improvements, quiz route changes, and associated endpoints.

## Updated Endpoints

### PDF Generation API
```
POST /api/pdf/generate
```
**Request**:
```json
{
  "user_id": "string",
  "quiz_responses": "object",
  "plan_data": "object"
}
```

**Response**:
```json
{
  "pdf_url": "string",
  "filename": "string",
  "food_suggestions": [
    {
      "meal_type": "breakfast|lunch|dinner",
      "food_combination": "string",
      "description": "string",
      "keto_friendly": "boolean"
    }
  ],
  "status": "string"
}
```

**Changes from base**: Now includes `food_suggestions` array with personalized recommendations based on quiz responses. PDF no longer contains blank pages.

### Meal Plan Retrieval
```
GET /api/meal-plans/{user_id}
```
**Response**:
```json
{
  "meal_plan_id": "string",
  "user_id": "string",
  "plan_data": "object",
  "pdf_url": "string",
  "created_at": "datetime",
  "food_suggestions": [
    {
      "meal_type": "breakfast|lunch|dinner",
      "food_combination": "string",
      "description": "string",
      "keto_friendly": "boolean"
    }
  ]
}
```

**Changes from base**: Now includes `food_suggestions` in response.

## New Endpoints

### Static Content API
```
GET /api/content/blog
```
**Response**:
```json
{
  "content": "string",
  "mistakes_section": [
    {
      "title": "string",
      "description": "string"
    }
  ],
  "last_updated": "datetime"
}
```

### Footer Links API (if dynamic)
```
GET /api/navigation/footer-links
```
**Response**:
```json
{
  "privacy_policy": {
    "url": "string",
    "title": "string"
  },
  "terms": {
    "url": "string",
    "title": "string"
  },
  "returns_policy": {
    "url": "string",
    "title": "string"
  }
}
```

## Frontend Route Changes

### Updated Routes
- `/` (homepage) - Now includes redesigned UI matching image.png and key features section
- `/quiz` - Moved quiz functionality to this route (previously at different location)

### New Routes
- `/blog` - Blog page with content from source file and mistakes section
- `/privacy-policy` - Static privacy policy page
- `/terms` - Static terms page
- `/returns-policy` - Static returns policy page

## Frontend Component Contracts

### Homepage Component Interface
```typescript
interface HomepageProps {
  heroBanner: {
    image: string;
    title: string;
    subtitle: string;
  };
  keyFeatures: Array<{
    icon: string;
    title: string;
    description: string;
  }>;
}
```

### PDF Generation Component Interface
```typescript
interface PDFGeneratorProps {
  quizData: QuizResponse;
  onGenerate: (pdfUrl: string, foodSuggestions: FoodSuggestion[]) => void;
  onError: (error: string) => void;
}
```

## Validation Requirements

### Request Validation
- All user input must be validated using Zod schemas
- Quiz responses must be complete before PDF generation
- File paths must be validated before content loading

### Response Validation
- PDF generation must return non-empty food suggestions array
- Blog content must be sanitized before API response
- All URLs in API responses must be valid

## Error Handling Contracts

### PDF Generation Errors
- `400`: Incomplete quiz responses
- `422`: Invalid quiz data format
- `500`: PDF generation failed
- `503`: External service timeout

### Content Loading Errors
- `404`: Content file not found
- `500`: Content processing failed

## Performance Requirements

- PDF generation must complete within 20 seconds
- Blog content must load within 3 seconds
- Homepage must render within 2 seconds
- All new pages must meet mobile-first responsive requirements