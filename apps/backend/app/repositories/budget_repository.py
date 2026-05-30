import uuid

from sqlalchemy import Select, func, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.enums import BudgetPeriodType

SORT_MAP = {
    "amount": Budget.amount,
    "created_at": Budget.created_at,
    "period_type": Budget.period_type,
    "position": Budget.position,
}


class BudgetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
        period_type: BudgetPeriodType | None = None,
        category_id: uuid.UUID | None = None,
        sort_by: str = "position",
        sort_order: str = "asc",
    ) -> tuple[list[Budget], int]:
        statement: Select[tuple[Budget]] = select(Budget).where(Budget.user_id == user_id)
        count_statement = select(func.count()).select_from(Budget).where(Budget.user_id == user_id)

        if period_type is not None:
            statement = statement.where(Budget.period_type == period_type)
            count_statement = count_statement.where(Budget.period_type == period_type)

        if category_id is not None:
            statement = statement.where(Budget.category_id == category_id)
            count_statement = count_statement.where(Budget.category_id == category_id)

        sort_column = SORT_MAP.get(sort_by, Budget.position)
        statement = statement.order_by(
            sort_column.asc() if sort_order == "asc" else sort_column.desc()
        )
        statement = statement.limit(limit).offset(offset)

        items = list(self.db.scalars(statement))
        total = self.db.scalar(count_statement) or 0
        return items, total

    def get_for_user(self, *, user_id: uuid.UUID, budget_id: uuid.UUID) -> Budget | None:
        statement = select(Budget).where(Budget.user_id == user_id, Budget.id == budget_id)
        return self.db.scalar(statement)

    def list_all_for_user(
        self,
        *,
        user_id: uuid.UUID,
        period_type: BudgetPeriodType | None = None,
        category_id: uuid.UUID | None = None,
        sort_by: str = "position",
        sort_order: str = "asc",
    ) -> list[Budget]:
        statement: Select[tuple[Budget]] = select(Budget).where(Budget.user_id == user_id)

        if period_type is not None:
            statement = statement.where(Budget.period_type == period_type)

        if category_id is not None:
            statement = statement.where(Budget.category_id == category_id)

        sort_column = SORT_MAP.get(sort_by, Budget.position)
        statement = statement.order_by(
            sort_column.asc() if sort_order == "asc" else sort_column.desc()
        )
        return list(self.db.scalars(statement))

    def find_existing(
        self,
        *,
        user_id: uuid.UUID,
        category_id: uuid.UUID,
        period_type: BudgetPeriodType,
    ) -> Budget | None:
        statement = select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.period_type == period_type,
        )
        return self.db.scalar(statement)

    def create(self, *, user_id: uuid.UUID, payload: dict[str, object]) -> Budget:
        budget = Budget(user_id=user_id, **payload)
        self.db.add(budget)
        self.db.flush()
        self.db.refresh(budget)
        return budget

    def update(self, budget: Budget, *, payload: dict[str, object]) -> Budget:
        for field, value in payload.items():
            setattr(budget, field, value)

        self.db.add(budget)
        self.db.flush()
        self.db.refresh(budget)
        return budget

    def delete(self, budget: Budget) -> None:
        self.db.delete(budget)
        self.db.flush()

    def delete_many_for_user(self, *, user_id: uuid.UUID, budget_ids: list[uuid.UUID]) -> int:
        if not budget_ids:
            return 0
        count = (
            self.db.scalar(
                select(func.count())
                .select_from(Budget)
                .where(Budget.user_id == user_id, Budget.id.in_(budget_ids))
            )
            or 0
        )
        self.db.execute(
            sa_delete(Budget).where(Budget.user_id == user_id, Budget.id.in_(budget_ids))
        )
        self.db.flush()
        return count

    def set_positions(self, *, user_id: uuid.UUID, ordered_ids: list[uuid.UUID]) -> None:
        for index, budget_id in enumerate(ordered_ids):
            self.db.execute(
                sa_update(Budget)
                .where(Budget.user_id == user_id, Budget.id == budget_id)
                .values(position=index)
            )
        self.db.flush()
