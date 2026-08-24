from fastapi import APIRouter

from app.api.routes.guardrail_router import router as guardrail_router
from app.api.routes.request_router import router as request_router
from app.api.routes.review_router import router as review_router
from app.api.routes.analytics_router import router as analytics_router
from app.api.routes.chat_router import router as chat_router
from app.api.routes.budget_router import router as budget_router
from app.api.routes.human_reviews_router import router as human_reviews_router

api_router = APIRouter()

api_router.include_router(guardrail_router)
api_router.include_router(request_router)
api_router.include_router(review_router)
api_router.include_router(analytics_router)
api_router.include_router(chat_router)
api_router.include_router(budget_router)
api_router.include_router(human_reviews_router)
