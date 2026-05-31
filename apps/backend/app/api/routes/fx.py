import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import CurrentUserId, DBSession
from app.repositories.exchange_rate_repository import ExchangeRateRepository
from app.schemas.exchange_rates import (
    ExchangeRateCreate,
    ExchangeRateListResponse,
    ExchangeRateRead,
)
from app.services.fx_service import FxService

router = APIRouter(prefix="/fx", tags=["fx"])


def get_fx_service(db: DBSession) -> FxService:
    return FxService(ExchangeRateRepository(db), db)


FxServiceDep = Annotated[FxService, Depends(get_fx_service)]


@router.get("/rates", response_model=ExchangeRateListResponse)
def list_rates(user_id: CurrentUserId, service: FxServiceDep) -> ExchangeRateListResponse:
    return service.list_rates(user_id=user_id)


@router.post("/rates", response_model=ExchangeRateRead, status_code=status.HTTP_201_CREATED)
def create_rate(
    payload: ExchangeRateCreate,
    user_id: CurrentUserId,
    service: FxServiceDep,
) -> ExchangeRateRead:
    rate = service.create_rate(user_id=user_id, payload=payload)
    return ExchangeRateRead.model_validate(rate)


@router.delete("/rates/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rate(
    rate_id: uuid.UUID,
    user_id: CurrentUserId,
    service: FxServiceDep,
) -> Response:
    service.delete_rate(user_id=user_id, rate_id=rate_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
