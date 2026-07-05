import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import CurrentUserId, DBSession
from app.core.config import settings
from app.repositories.exchange_rate_repository import ExchangeRateRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.settings_repository import SettingsRepository
from app.schemas.portfolio import (
    HoldingContributionCreate,
    HoldingCreate,
    HoldingListResponse,
    HoldingPriceUpdate,
    HoldingRead,
    HoldingUpdate,
    PortfolioSummaryRead,
    PriceRefreshItem,
    PriceRefreshResponse,
)
from app.services.fx_service import CurrencyConverter
from app.services.portfolio_service import PortfolioService
from app.services.price_fetch_service import (
    CoinGeckoProvider,
    PriceFetchService,
    TwelveDataProvider,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def get_portfolio_service(db: DBSession) -> PortfolioService:
    return PortfolioService(HoldingRepository(db), PriceRepository(db), db)


PortfolioServiceDep = Annotated[PortfolioService, Depends(get_portfolio_service)]


def get_price_fetch_service(db: DBSession) -> PriceFetchService:
    stock_provider = (
        TwelveDataProvider(settings.twelvedata_api_key) if settings.twelvedata_api_key else None
    )
    return PriceFetchService(
        HoldingRepository(db),
        PriceRepository(db),
        db,
        crypto_provider=CoinGeckoProvider(),
        stock_provider=stock_provider,
    )


PriceFetchServiceDep = Annotated[PriceFetchService, Depends(get_price_fetch_service)]


@router.get("/summary", response_model=PortfolioSummaryRead)
def get_portfolio_summary(
    user_id: CurrentUserId,
    service: PortfolioServiceDep,
    db: DBSession,
) -> PortfolioSummaryRead:
    settings = SettingsRepository(db).get_for_user(user_id=user_id)
    base_currency = settings.default_currency if settings is not None else None
    converter = CurrencyConverter(
        ExchangeRateRepository(db).latest_rates_for_user(user_id=user_id)
    )
    return service.get_summary(
        user_id=user_id,
        base_currency=base_currency,
        converter=converter,
    )


@router.post("/prices/refresh", response_model=PriceRefreshResponse)
def refresh_prices(
    user_id: CurrentUserId,
    service: PriceFetchServiceDep,
) -> PriceRefreshResponse:
    result = service.refresh_prices(user_id=user_id)
    return PriceRefreshResponse(
        updated=[PriceRefreshItem(**item) for item in result.updated],
        failed=[PriceRefreshItem(**item) for item in result.failed],
    )


@router.get("/holdings", response_model=HoldingListResponse)
def list_holdings(
    user_id: CurrentUserId,
    service: PortfolioServiceDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: Literal["asset_name", "created_at"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> HoldingListResponse:
    return service.list_holdings(
        user_id=user_id,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("/holdings", response_model=HoldingRead, status_code=status.HTTP_201_CREATED)
def create_holding(
    payload: HoldingCreate,
    user_id: CurrentUserId,
    service: PortfolioServiceDep,
) -> HoldingRead:
    holding = service.create_holding(user_id=user_id, payload=payload)
    return HoldingRead.model_validate(holding)


@router.get("/holdings/{holding_id}", response_model=HoldingRead)
def get_holding(
    holding_id: uuid.UUID,
    user_id: CurrentUserId,
    service: PortfolioServiceDep,
) -> HoldingRead:
    holding = service.get_holding(user_id=user_id, holding_id=holding_id)
    return HoldingRead.model_validate(holding)


@router.patch("/holdings/{holding_id}", response_model=HoldingRead)
def update_holding(
    holding_id: uuid.UUID,
    payload: HoldingUpdate,
    user_id: CurrentUserId,
    service: PortfolioServiceDep,
) -> HoldingRead:
    holding = service.update_holding(user_id=user_id, holding_id=holding_id, payload=payload)
    return HoldingRead.model_validate(holding)


@router.post("/holdings/{holding_id}/price", response_model=HoldingRead)
def update_holding_price(
    holding_id: uuid.UUID,
    payload: HoldingPriceUpdate,
    user_id: CurrentUserId,
    service: PortfolioServiceDep,
) -> HoldingRead:
    holding = service.update_price(user_id=user_id, holding_id=holding_id, price=payload.price)
    return HoldingRead.model_validate(holding)


@router.post("/holdings/{holding_id}/contribution", response_model=HoldingRead)
def add_holding_contribution(
    holding_id: uuid.UUID,
    payload: HoldingContributionCreate,
    user_id: CurrentUserId,
    service: PortfolioServiceDep,
) -> HoldingRead:
    holding = service.add_contribution(user_id=user_id, holding_id=holding_id, payload=payload)
    return HoldingRead.model_validate(holding)


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holding(
    holding_id: uuid.UUID,
    user_id: CurrentUserId,
    service: PortfolioServiceDep,
) -> Response:
    service.delete_holding(user_id=user_id, holding_id=holding_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
