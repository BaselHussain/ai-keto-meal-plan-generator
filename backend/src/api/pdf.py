from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ..services.pdf_service import generate_pdf_with_suggestions
from ..models.user import User
from ..api.quiz import get_current_user
from ..pdf.generator import create_enhanced_pdf, generate_food_suggestions

router = APIRouter(prefix="/api/pdf", tags=["PDF Generation"])


class MealPlanData(BaseModel):
    daily_meals: List[Dict[str, Any]]


class QuizResponses(BaseModel):
    gender: Optional[str] = None
    activity_level: Optional[str] = None
    meat_preference: Optional[str] = None
    fish_variety: Optional[str] = None
    vegetables: Optional[List[str]] = None
    other_preferences: Optional[Dict[str, Any]] = None


class PDFGenerationRequest(BaseModel):
    user_id: str
    quiz_responses: QuizResponses
    plan_data: MealPlanData


class FoodSuggestion(BaseModel):
    meal_type: str  # breakfast, lunch, dinner, snack
    food_combination: str
    description: str
    keto_friendly: bool


class PDFGenerationResponse(BaseModel):
    pdf_url: str
    filename: str
    food_suggestions: List[FoodSuggestion]
    status: str


@router.post("/generate", response_model=PDFGenerationResponse)
async def generate_enhanced_pdf(
    request: PDFGenerationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate an enhanced PDF with meal plan and personalized food suggestions
    """
    try:
        # Generate personalized food suggestions based on quiz responses
        food_suggestions = generate_food_suggestions(request.quiz_responses.dict())

        # Create the enhanced PDF with food suggestions
        pdf_content = create_enhanced_pdf(
            request.plan_data.dict(),
            request.quiz_responses.dict(),
            food_suggestions
        )

        # TODO: Implement PDF storage in blob storage
        # For now, returning placeholder response
        return PDFGenerationResponse(
            pdf_url=f"/api/download/{current_user.id}/meal-plan.pdf",
            filename=f"30-day-keto-meal-plan-{current_user.id}.pdf",
            food_suggestions=food_suggestions,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


class MealPlanResponse(BaseModel):
    meal_plan_id: str
    user_id: str
    plan_data: MealPlanData
    pdf_url: str
    created_at: str
    food_suggestions: List[FoodSuggestion]


@router.get("/meal-plan/{user_id}", response_model=MealPlanResponse)
async def get_meal_plan_with_suggestions(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve meal plan with food suggestions for a user
    """
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this meal plan")

    # TODO: Implement actual meal plan retrieval from database
    # For now, returning placeholder response
    return MealPlanResponse(
        meal_plan_id="placeholder_id",
        user_id=user_id,
        plan_data=MealPlanData(daily_meals=[]),
        pdf_url=f"/api/download/{user_id}/meal-plan.pdf",
        created_at="2026-02-27T00:00:00Z",
        food_suggestions=[]
    )