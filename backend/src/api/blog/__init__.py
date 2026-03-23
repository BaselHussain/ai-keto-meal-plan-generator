"""
Blog API Routes

API Endpoints:
- GET /api/v1/blog/content - Retrieve blog content with keto diet information and mistakes to avoid
"""

from fastapi import APIRouter
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/blog", tags=["Blog"])

# Models
class BlogContent(BaseModel):
    """Model for blog content response"""
    title: str
    content: str
    key_takeaways: List[str]
    mistakes_to_avoid: List[str]

# Sample content based on the document
BLOG_CONTENT = BlogContent(
    title="Keto Diet Insights & Personalization",
    content="Starting a weight loss journey can be tough, but with the right help, it's doable and lasting. The Custom Keto Diet Meal Plan gives you a plan made just for you. It fits your needs and likes.\n\nWhy Personalization Matters in Keto Dieting\nPersonalization is crucial for diet success, especially with the keto diet. A custom keto plan considers your nutritional needs and goals. It makes the diet effective and easy to stick to.\nPersonalizing your keto plan can:\nMake sticking to the diet easier\nImprove nutritional balance\nHelp you lose and keep off weight\n\nWhat Is a Custom Keto Diet Meal Plan\nA custom keto diet meal plan is made just for you. It helps you get into ketosis by focusing on what you need and like. This way, you can stick to it and enjoy it.\nTo make a custom keto diet meal plan, we look at your health, what you like to eat, and your lifestyle. We use this info to create a meal plan that helps you get into ketosis. It also makes sure you get all the nutrients you need and that you're happy with your food choices.\n\nHow the Personalization Process Works?\nFirst, we ask you a lot of questions. We want to know about your health goals, food likes, and how you live your life. This helps us figure out the best diet plan for you.\nWe look at your weight, how active you are, and any food rules you have. Then, we create a meal plan just for you. It's designed to help you do well on the keto diet.\n\nThe Difference Between Generic and Custom Keto Plans\nGeneric keto plans are the same for everyone. They might not work as well for people with special needs or tastes. Custom keto plans, on the other hand, are made just for you. They offer a better way to get into and stay in ketosis.\nChoosing a custom keto diet meal plan means you get a diet that really works for you. It's a great way to lose weight and improve your health.",
    key_takeaways=[
        "A personalized approach to weight loss through a tailored keto plan",
        "Includes a meal plan, food selection report, and shopping list for ease",
        "Simplifies the keto diet process with calorie estimates and food combination guidance",
        "Highlights common keto mistakes to avoid for better results",
        "Designed for individuals seeking a structured weight loss journey",
        "Supports healthy and sustainable weight loss"
    ],
    mistakes_to_avoid=[
        "Not tracking your macros properly - It's important to maintain the right balance of fats, proteins, and carbs to stay in ketosis",
        "Eating too much protein - Excessive protein can kick you out of ketosis as it can be converted to glucose",
        "Not drinking enough water - Dehydration is common when starting keto due to water loss from glycogen depletion",
        "Neglecting electrolytes - Low carb diets can cause electrolyte imbalances leading to keto flu symptoms",
        "Consuming hidden carbs in 'keto-friendly' products - Many processed keto foods contain hidden carbs that add up",
        "Going too low on carbs too quickly - This can cause uncomfortable side effects and make the transition harder",
        "Not eating enough healthy fats - On keto, fats become your primary energy source, so they're crucial",
        "Skipping meals or not eating enough - This can lead to energy crashes and difficulty maintaining the diet",
        "Not planning meals ahead - Lack of planning can lead to poor food choices when you're hungry",
        "Comparing your progress to others - Everyone's journey is different, and individual results vary based on many factors"
    ]
)

@router.get("/content", response_model=BlogContent)
async def get_blog_content():
    """
    Retrieve blog content with keto diet information and common mistakes to avoid.

    This endpoint provides educational content about the keto diet, personalization
    importance, and common mistakes to avoid during the keto journey.

    Returns:
        BlogContent: The blog content with key takeaways and common mistakes
    """
    return BLOG_CONTENT