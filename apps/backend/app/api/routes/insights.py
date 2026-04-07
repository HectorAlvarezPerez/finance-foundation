from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUserId, DBSession
from app.llm.runtime import build_llm_runtime
from app.repositories.account_repository import AccountRepository
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.monthly_insight_recap_repository import MonthlyInsightRecapRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.insights import (
    InsightsMonthlyRecapRead,
    InsightsMonthlyRecapRegenerateRequest,
    InsightsSummaryRead,
)
from app.services.azure_openai_monthly_recap_service import AzureOpenAIMonthlyRecapService
from app.services.insights_service import InsightsService
from app.services.monthly_recap_service import MonthlyRecapService

router = APIRouter(prefix="/insights", tags=["insights"])


def get_insights_service(db: DBSession) -> InsightsService:
    return InsightsService(
        AccountRepository(db),
        CategoryRepository(db),
        TransactionRepository(db),
    )


InsightsServiceDep = Annotated[InsightsService, Depends(get_insights_service)]


def get_monthly_recap_service(db: DBSession) -> MonthlyRecapService:
    llm_runtime = build_llm_runtime()
    insights_service = get_insights_service(db)
    return MonthlyRecapService(
        insights_service=insights_service,
        budget_repository=BudgetRepository(db),
        recap_repository=MonthlyInsightRecapRepository(db),
        db=db,
        prompt_provider=llm_runtime.prompt_provider,
        observability_client=llm_runtime.observability_client,
        narrative_service=AzureOpenAIMonthlyRecapService(
            prompt_provider=llm_runtime.prompt_provider,
            observability_client=llm_runtime.observability_client,
        ),
    )


MonthlyRecapServiceDep = Annotated[MonthlyRecapService, Depends(get_monthly_recap_service)]


@router.get("/summary", response_model=InsightsSummaryRead)
def get_insights_summary(
    user_id: CurrentUserId,
    service: InsightsServiceDep,
) -> InsightsSummaryRead:
    return service.get_summary(user_id=user_id)


@router.get("/monthly-recap", response_model=InsightsMonthlyRecapRead)
def get_monthly_recap(
    user_id: CurrentUserId,
    service: MonthlyRecapServiceDep,
    month_key: str = Query(pattern=r"^\d{4}-\d{2}$"),
) -> InsightsMonthlyRecapRead:
    return service.get_monthly_recap(user_id=user_id, month_key=month_key)


@router.post("/monthly-recap/regenerate", response_model=InsightsMonthlyRecapRead)
def regenerate_monthly_recap(
    payload: InsightsMonthlyRecapRegenerateRequest,
    user_id: CurrentUserId,
    service: MonthlyRecapServiceDep,
) -> InsightsMonthlyRecapRead:
    return service.regenerate_monthly_recap(user_id=user_id, month_key=payload.month_key)
