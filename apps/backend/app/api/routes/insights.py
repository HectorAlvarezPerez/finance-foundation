from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUserId, DBSession
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.insights import InsightsSummaryRead
from app.services.insights_service import InsightsService

router = APIRouter(prefix="/insights", tags=["insights"])


def get_insights_service(db: DBSession) -> InsightsService:
    return InsightsService(
        AccountRepository(db),
        CategoryRepository(db),
        TransactionRepository(db),
    )


InsightsServiceDep = Annotated[InsightsService, Depends(get_insights_service)]


@router.get("/summary", response_model=InsightsSummaryRead)
def get_insights_summary(
    user_id: CurrentUserId,
    service: InsightsServiceDep,
) -> InsightsSummaryRead:
    return service.get_summary(user_id=user_id)
