import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.budget import Budget
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


class BudgetService:
    def __init__(
        self,
        repository: BudgetRepository,
        category_repository: CategoryRepository,
        db: Session,
    ) -> None:
        self.repository = repository
        self.category_repository = category_repository
        self.db = db

    def list_budgets(
        self,
        *,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
        year: int | None = None,
        month: int | None = None,
        period_type: BudgetPeriodType | None = None,
        category_id: uuid.UUID | None = None,
        sort_by: str = "year",
        sort_order: str = "desc",
    ) -> BudgetListResponse:
        items, total = self.repository.list_for_user(
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
        return BudgetListResponse(
            items=[BudgetRead.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_budget(self, *, user_id: uuid.UUID, budget_id: uuid.UUID) -> Budget:
        budget = self.repository.get_for_user(user_id=user_id, budget_id=budget_id)
        if budget is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
        return budget

    def create_budget(self, *, user_id: uuid.UUID, payload: BudgetCreate) -> Budget:
        self._require_category(user_id=user_id, category_id=payload.category_id)
        duplicate = self.repository.find_existing(
            user_id=user_id,
            category_id=payload.category_id,
            year=payload.year,
            period_type=payload.period_type,
            month=payload.month,
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=self._build_duplicate_message(payload.period_type),
            )
        budget = self.repository.create(user_id=user_id, payload=payload.model_dump())
        self.db.commit()
        return budget

    def create_budgets_bulk(
        self,
        *,
        user_id: uuid.UUID,
        payload: BudgetBulkCreate,
    ) -> BudgetBulkCreateResponse:
        self._require_category(user_id=user_id, category_id=payload.category_id)

        duplicate_months = self.repository.find_existing_months(
            user_id=user_id,
            category_id=payload.category_id,
            year=payload.year,
            months=payload.months,
        )
        if duplicate_months:
            month_list = ", ".join(str(month) for month in duplicate_months)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un presupuesto para los meses: {month_list}",
            )

        created_items = self.repository.create_many(
            user_id=user_id,
            payloads=[
                {
                    "category_id": payload.category_id,
                    "year": payload.year,
                    "month": month,
                    "currency": payload.currency,
                    "amount": payload.amount,
                }
                for month in payload.months
            ],
        )
        self.db.commit()
        return BudgetBulkCreateResponse(
            items=[BudgetRead.model_validate(item) for item in created_items],
            created_count=len(created_items),
        )

    def update_budget(
        self,
        *,
        user_id: uuid.UUID,
        budget_id: uuid.UUID,
        payload: BudgetUpdate,
    ) -> Budget:
        budget = self.get_budget(user_id=user_id, budget_id=budget_id)
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return budget

        category_id = updates.get("category_id", budget.category_id)
        year = updates.get("year", budget.year)
        period_type = updates.get("period_type", budget.period_type)
        if period_type == BudgetPeriodType.ANNUAL and "month" not in updates:
            updates["month"] = None

        month = updates.get("month", budget.month)
        if period_type == BudgetPeriodType.MONTHLY and month is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month is required for monthly budgets",
            )

        self._require_category(user_id=user_id, category_id=category_id)

        duplicate = self.repository.find_existing(
            user_id=user_id,
            category_id=category_id,
            year=year,
            period_type=period_type,
            month=month,
        )
        if duplicate is not None and duplicate.id != budget.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=self._build_duplicate_message(period_type),
            )

        budget = self.repository.update(budget, payload=updates)
        self.db.commit()
        return budget

    def delete_budget(self, *, user_id: uuid.UUID, budget_id: uuid.UUID) -> None:
        budget = self.get_budget(user_id=user_id, budget_id=budget_id)
        self.repository.delete(budget)
        self.db.commit()

    def _require_category(self, *, user_id: uuid.UUID, category_id: uuid.UUID) -> None:
        category = self.category_repository.get_for_user(user_id=user_id, category_id=category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected category does not exist for the current user",
            )

    @staticmethod
    def _build_duplicate_message(period_type: BudgetPeriodType) -> str:
        if period_type == BudgetPeriodType.ANNUAL:
            return "An annual budget already exists for this category and year"
        return "A budget already exists for this category and month"
