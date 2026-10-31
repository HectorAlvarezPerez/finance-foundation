from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUserId, DBSession
from app.llm.runtime import build_llm_runtime
from app.repositories.account_repository import AccountRepository
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.exchange_rate_repository import ExchangeRateRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.monthly_insight_recap_repository import MonthlyInsightRecapRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.insights import (
    InsightsMonthlyRecapRead,
    InsightsMonthlyRecapRegenerateRequest,
    InsightsSummaryRead,
    NetWorthRead,
    SubscriptionsRead,
)
from app.services.azure_openai_monthly_recap_service import AzureOpenAIMonthlyRecapService
from app.services.fx_service import CurrencyConverter
from app.services.insights_service import InsightsService
from app.services.monthly_recap_service import MonthlyRecapService
from app.services.portfolio_service import PortfolioService

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
    db: DBSession,
    month_key: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
) -> InsightsSummaryRead:
    settings = SettingsRepository(db).get_for_user(user_id=user_id)
    base_currency = settings.default_currency if settings is not None else None
    converter = CurrencyConverter(
        ExchangeRateRepository(db).latest_rates_for_user(user_id=user_id)
    )
    return service.get_summary(
        user_id=user_id,
        base_currency=base_currency,
        converter=converter,
        month_key=month_key,
    )


@router.get("/net-worth", response_model=NetWorthRead)
def get_net_worth(
    user_id: CurrentUserId,
    service: InsightsServiceDep,
    db: DBSession,
) -> NetWorthRead:
    settings_obj = SettingsRepository(db).get_for_user(user_id=user_id)
    base_currency = settings_obj.default_currency if settings_obj is not None else None
    converter = CurrencyConverter(
        ExchangeRateRepository(db).latest_rates_for_user(user_id=user_id)
    )
    accounts_value, history = service.get_net_worth_history(
        user_id=user_id,
        base_currency=base_currency,
        converter=converter,
    )
    portfolio = PortfolioService(HoldingRepository(db), PriceRepository(db), db).get_summary(
        user_id=user_id,
        base_currency=base_currency,
        converter=converter,
    )
    investments_value = portfolio.total_value
    return NetWorthRead(
        currency=base_currency,
        accounts_value=accounts_value,
        investments_value=investments_value,
        net_worth=accounts_value + investments_value,
        history=history,
    )


@router.get("/subscriptions", response_model=SubscriptionsRead)
def get_subscriptions(
    user_id: CurrentUserId,
    service: InsightsServiceDep,
    db: DBSession,
) -> SubscriptionsRead:
    settings_obj = SettingsRepository(db).get_for_user(user_id=user_id)
    base_currency = settings_obj.default_currency if settings_obj is not None else None
    converter = CurrencyConverter(
        ExchangeRateRepository(db).latest_rates_for_user(user_id=user_id)
    )
    items, total = service.detect_subscriptions(
        user_id=user_id,
        base_currency=base_currency,
        converter=converter,
    )
    return SubscriptionsRead(
        currency=base_currency,
        total_monthly_estimate=total,
        items=items,
    )


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
