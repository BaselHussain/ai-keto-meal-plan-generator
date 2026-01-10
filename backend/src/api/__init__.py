"""
API Router Registry

Central registry for all API routers. All route modules should be imported
and included here for automatic mounting to the main FastAPI app.

Router Structure:
- /api/v1/health - Health check endpoint
- /api/v1/auth - Authentication endpoints (future)
- /api/v1/quiz - Quiz submission endpoints (future)
- /api/v1/meal-plans - Meal plan generation endpoints (future)
- /api/v1/payments - Payment webhook endpoints (future)
- /api/v1/admin - Admin endpoints (future)
"""

from fastapi import APIRouter

# Import route modules
from src.api.health import router as health_router

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(health_router, tags=["Health"])

# Add more routers as they are implemented:
# api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(quiz_router, prefix="/quiz", tags=["Quiz"])
# api_router.include_router(meal_plan_router, prefix="/meal-plans", tags=["Meal Plans"])
# api_router.include_router(payment_router, prefix="/payments", tags=["Payments"])
# api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
