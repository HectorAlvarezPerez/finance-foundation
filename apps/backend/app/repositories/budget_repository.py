import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.budget import Budget


class BudgetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
        year: int | None = None,
        month: int | None = None,
        category_id: uuid.UUID | None = None,
        sort_by: str = "year",
        sort_order: str = "desc",
    ) -> tuple[list[Budget], int]:
        statement: Select[tuple[Budget]] = select(Budget).where(Budget.user_id == user_id)
        count_statement = select(func.count()).select_from(Budget).where(Budget.user_id == user_id)

        if year is not None:
            statement = statement.where(Budget.year == year)
            count_statement = count_statement.where(Budget.year == year)

        if month is not None:
            statement = statement.where(Budget.month == month)
            count_statement = count_statement.where(Budget.month == month)

        if category_id is not None:
            statement = statement.where(Budget.category_id == category_id)
            count_statement = count_statement.where(Budget.category_id == category_id)

        sort_map = {
            "amount": Budget.amount,
            "created_at": Budget.created_at,
            "month": Budget.month,
            "year": Budget.year,
        }
        sort_column = sort_map.get(sort_by, Budget.year)
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

    def find_existing(
        self,
        *,
        user_id: uuid.UUID,
        category_id: uuid.UUID,
        year: int,
        month: int,
    ) -> Budget | None:
        statement = select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.year == year,
            Budget.month == month,
        )
        return self.db.scalar(statement)

    def find_existing_months(
        self,
        *,
        user_id: uuid.UUID,
        category_id: uuid.UUID,
        year: int,
        months: list[int],
    ) -> list[int]:
        if not months:
            return []

        statement = select(Budget.month).where(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.year == year,
            Budget.month.in_(months),
        )
        return sorted(list(self.db.scalars(statement)))

    def create(self, *, user_id: uuid.UUID, payload: dict[str, object]) -> Budget:
        budget = Budget(user_id=user_id, **payload)
        self.db.add(budget)
        self.db.flush()
        self.db.refresh(budget)
        return budget

    def create_many(self, *, user_id: uuid.UUID, payloads: list[dict[str, object]]) -> list[Budget]:
        items: list[Budget] = []
        for payload in payloads:
            budget = Budget(user_id=user_id, **payload)
            self.db.add(budget)
            items.append(budget)

        self.db.flush()
        for budget in items:
            self.db.refresh(budget)
        return items

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
