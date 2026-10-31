import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import BudgetPeriodType, CategoryType
from app.models.transaction import Transaction
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.schemas.budgets import (
    BudgetCreate,
    BudgetListResponse,
    BudgetRead,
    BudgetSpendItem,
    BudgetSpendResponse,
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
        period_type: BudgetPeriodType | None = None,
        category_id: uuid.UUID | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> BudgetListResponse:
        items, total = self.repository.list_for_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
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

    def get_spend(self, *, user_id: uuid.UUID, year: int) -> BudgetSpendResponse:
        """Aggregate expense spend per category per month for one year.

        Only transactions in expense-type categories count; transfer legs
        (any transaction with a ``transfer_group_id``) are excluded. Positive
        amounts in expense categories (refunds) net against spend:
        ``spent = -(sum of signed amounts)``, floored at 0 per category-month
        (category-months that net to zero or below are omitted).
        """
        month_expr = extract("month", Transaction.date)
        statement = (
            select(
                Transaction.category_id,
                month_expr.label("month"),
                func.sum(Transaction.amount).label("total"),
            )
            .join(Category, Category.id == Transaction.category_id)
            .where(
                Transaction.user_id == user_id,
                Category.type == CategoryType.EXPENSE,
                Transaction.transfer_group_id.is_(None),
                Transaction.date >= date(year, 1, 1),
                Transaction.date <= date(year, 12, 31),
            )
            .group_by(Transaction.category_id, month_expr)
        )

        items: list[BudgetSpendItem] = []
        for category_id, month, total in self.db.execute(statement):
            if category_id is None or total is None:
                continue
            total_decimal = total if isinstance(total, Decimal) else Decimal(str(total))
            spent = -total_decimal
            if spent <= 0:
                continue
            items.append(
                BudgetSpendItem(category_id=category_id, month=int(month), spent=spent)
            )

        items.sort(key=lambda item: (str(item.category_id), item.month))
        return BudgetSpendResponse(year=year, items=items)

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
            period_type=payload.period_type,
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=self._build_duplicate_message(payload.period_type),
            )
        budget = self.repository.create(user_id=user_id, payload=payload.model_dump())
        self.db.commit()
        return budget

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
        period_type = updates.get("period_type", budget.period_type)

        self._require_category(user_id=user_id, category_id=category_id)

        duplicate = self.repository.find_existing(
            user_id=user_id,
            category_id=category_id,
            period_type=period_type,
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

    def delete_budgets(self, *, user_id: uuid.UUID, budget_ids: list[uuid.UUID]) -> int:
        deleted_count = self.repository.delete_many_for_user(
            user_id=user_id,
            budget_ids=budget_ids,
        )
        self.db.commit()
        return deleted_count

    def reorder_budgets(self, *, user_id: uuid.UUID, budget_ids: list[uuid.UUID]) -> None:
        owned = {budget.id for budget in self.repository.list_all_for_user(user_id=user_id)}
        unknown = [budget_id for budget_id in budget_ids if budget_id not in owned]
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more budgets do not exist for the current user",
            )
        self.repository.set_positions(user_id=user_id, ordered_ids=budget_ids)
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
            return "Ya existe un presupuesto anual para esta categoría"
        return "Ya existe un presupuesto mensual para esta categoría"
