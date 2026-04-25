import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import CurrentUserId, DBSession
from app.models.enums import BudgetPeriodType
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.schemas.budgets import (
    BudgetBulkCreate,
    BudgetBulkCreateResponse,
    BudgetCreate,
    BudgetListResponse,
    BudgetRead,
    BudgetUpdate,
)
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/budgets", tags=["budgets"])


def get_budget_service(db: DBSession) -> BudgetService:
    return BudgetService(BudgetRepository(db), CategoryRepository(db), db)


BudgetServiceDep = Annotated[BudgetService, Depends(get_budget_service)]


@router.get("", response_model=BudgetListResponse)
def list_budgets(
    user_id: CurrentUserId,
    service: BudgetServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    period_type: BudgetPeriodType | None = None,
    category_id: uuid.UUID | None = None,
    sort_by: Literal["amount", "created_at", "month", "period_type", "year"] = "year",
    sort_order: Literal["asc", "desc"] = "desc",
) -> BudgetListResponse:
    return service.list_budgets(
        user_id=user_id,
        limit=limit,
        offset=offset,
        year=year,
        month=month,
        period_type=period_type,
        category_id=category_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    user_id: CurrentUserId,
    service: BudgetServiceDep,
) -> BudgetRead:
    budget = service.create_budget(user_id=user_id, payload=payload)
    return BudgetRead.model_validate(budget)


@router.post("/bulk", response_model=BudgetBulkCreateResponse, status_code=status.HTTP_201_CREATED)
def create_budgets_bulk(
    payload: BudgetBulkCreate,
    user_id: CurrentUserId,
    service: BudgetServiceDep,
) -> BudgetBulkCreateResponse:
    return service.create_budgets_bulk(user_id=user_id, payload=payload)


@router.get("/{budget_id}", response_model=BudgetRead)
def get_budget(
    budget_id: uuid.UUID,
    user_id: CurrentUserId,
    service: BudgetServiceDep,
) -> BudgetRead:
    budget = service.get_budget(user_id=user_id, budget_id=budget_id)
    return BudgetRead.model_validate(budget)


@router.patch("/{budget_id}", response_model=BudgetRead)
def update_budget(
    budget_id: uuid.UUID,
    payload: BudgetUpdate,
    user_id: CurrentUserId,
    service: BudgetServiceDep,
) -> BudgetRead:
    budget = service.update_budget(user_id=user_id, budget_id=budget_id, payload=payload)
    return BudgetRead.model_validate(budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: uuid.UUID,
    user_id: CurrentUserId,
    service: BudgetServiceDep,
) -> Response:
    service.delete_budget(user_id=user_id, budget_id=budget_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
