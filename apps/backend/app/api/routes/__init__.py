from app.api.routes.accounts import router as accounts_router
from app.api.routes.categories import router as categories_router
from app.api.routes.health import router as health_router
from app.api.routes.transactions import router as transactions_router

__all__ = [
    "accounts_router",
    "categories_router",
    "health_router",
    "transactions_router",
]
