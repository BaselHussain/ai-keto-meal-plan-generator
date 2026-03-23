# Data Model: UI & PDF Enhancements

**Feature**: UI & PDF Enhancements
**Date**: 2026-02-27
**Author**: Claude

## Entity Relationships

### Homepage UI
- **Type**: UI/Display Entity
- **Fields**:
  - hero_banner: string (image reference from image.png)
  - layout_config: json (positioning and styling matching image.png)
  - features: array (5-6 key features with icons)
- **Validation**: Must match visual design from image.png

### PDF Meal Plan (Enhanced)
- **Type**: Document Entity
- **Fields**:
  - id: UUID
  - user_id: UUID (foreign key to user)
  - meal_plan_data: json (30-day plan)
  - food_suggestions: array (5 personalized combinations)
  - created_at: datetime
  - pdf_url: string (blob storage URL)
- **Validation**:
  - No blank pages after generation
  - Must include 5 food suggestions based on quiz responses
  - Maintain keto compliance standards

### Quiz Route
- **Type**: Navigation Entity
- **Fields**:
  - path: string (should be "/quiz")
  - navigation_label: string
  - active: boolean
- **State transitions**: Active/inactive based on user journey stage

### Footer Component
- **Type**: UI Component Entity
- **Fields**:
  - privacy_link: string (URL)
  - terms_link: string (URL)
  - returns_link: string (URL)
  - display: boolean
- **Validation**: All links must be valid and accessible

### Blog Content
- **Type**: Content Entity
- **Fields**:
  - content_source: string (path to Custom keto diet meal plan change final.md)
  - mistakes_section: array (5-10 common keto mistakes)
  - slug: string (for /blog route)
  - published_date: datetime
  - content_type: enum ("markdown", "html")
- **Validation**: Content must be sanitized before rendering

## API Contract Requirements

### Frontend Changes
1. **GET /** - Updated homepage with new UI elements and features section
2. **GET /quiz** - Moved quiz route (previously at different location)
3. **GET /blog** - New route with content from external file and mistakes section
4. **GET /privacy-policy, /terms, /returns-policy** - New static routes

### Backend Changes
1. **POST /api/pdf/generate** - Enhanced to include food suggestions in output
2. **PUT /api/pdf/remove-blank-page** - Internal improvement to PDF generation process

## Database Considerations

### Existing Tables Affected
- **meal_plans** table: No schema changes, only content generation logic updated

### New Content Requirements
- Static content for privacy policy, terms, and returns pages will be stored as part of the Next.js application build
- Blog content will be loaded from external file at build time or runtime depending on implementation

## Validation Rules

1. **PDF Enhancement Validation**:
   - Generated PDF must have exactly the same number of pages as intended content (no blank pages)
   - Food suggestions must be personalized based on quiz response data
   - All meal plan components must maintain keto compliance (<30g net carbs/day)

2. **UI Validation**:
   - Homepage design must match image.png exactly in terms of layout and styling
   - All new routes must be responsive and mobile-friendly
   - Footer links must point to valid, accessible pages

3. **Content Validation**:
   - Blog content from external file must be properly sanitized
   - Mistakes section must contain 5-10 relevant, helpful keto mistakes to avoid