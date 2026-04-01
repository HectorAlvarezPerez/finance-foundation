from fastapi import APIRouter

from app.api.routes.accounts import router as accounts_router
from app.api.routes.auth import router as auth_router
from app.api.routes.budgets import router as budgets_router
from app.api.routes.categories import router as categories_router
from app.api.routes.health import router as health_router
from app.api.routes.insights import router as insights_router
from app.api.routes.settings import router as settings_router
from app.api.routes.transactions import router as transactions_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(health_router, tags=["health"])
api_router.include_router(accounts_router)
api_router.include_router(budgets_router)
api_router.include_router(categories_router)
api_router.include_router(insights_router)
api_router.include_router(settings_router)
api_router.include_router(transactions_router)
