"""
API Router Registry

Central registry for all API routers. All route modules should be imported
and included here for automatic mounting to the main FastAPI app.

Router Structure:
- /api/v1/health - Health check endpoint
- /api/v1/quiz - Quiz submission endpoints
- /api/v1/verification - Email verification endpoints
- /api/v1/recovery - Magic link recovery endpoints
- /api/v1/auth - Authentication endpoints (account registration)
- /api/v1/download - PDF download endpoints with rate limiting
- /api/v1/meal-plans - Meal plan generation endpoints (future)
- /api/v1/payments - Payment webhook endpoints (future)
- /api/v1/admin - Admin endpoints (future)
"""

import os

from fastapi import APIRouter

# Import route modules
from src.api.health import router as health_router
from src.api.quiz import router as quiz_router
from src.api.verification import router as verification_router
from src.api.recovery import router as recovery_router
from src.api.auth import router as auth_router
from src.api.download import router as download_router
from src.api.admin import router as admin_router
from src.api.payment import router as payment_router

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(quiz_router, tags=["Quiz"])
api_router.include_router(verification_router, tags=["Verification"])
api_router.include_router(recovery_router, tags=["Recovery"])
api_router.include_router(auth_router, tags=["Authentication"])
api_router.include_router(download_router, tags=["Download"])
api_router.include_router(admin_router, tags=["Admin"])
api_router.include_router(payment_router, tags=["Payment"])

# Dev-only router (NOT available in production)
if os.getenv("ENV", "development") != "production":
    from src.api.dev import router as dev_router
    api_router.include_router(dev_router, tags=["Development"])

# Add more routers as they are implemented:
# api_router.include_router(meal_plan_router, prefix="/meal-plans", tags=["Meal Plans"])
# api_router.include_router(payment_router, prefix="/payments", tags=["Payments"])
