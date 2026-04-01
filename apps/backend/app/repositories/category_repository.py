import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import CategoryType


class CategoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
        category_type: CategoryType | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Category], int]:
        statement: Select[tuple[Category]] = select(Category).where(Category.user_id == user_id)
        count_statement = (
            select(func.count()).select_from(Category).where(Category.user_id == user_id)
        )

        if category_type is not None:
            statement = statement.where(Category.type == category_type)
            count_statement = count_statement.where(Category.type == category_type)

        sort_column = Category.name if sort_by == "name" else Category.created_at
        statement = statement.order_by(
            sort_column.asc() if sort_order == "asc" else sort_column.desc()
        )
        statement = statement.limit(limit).offset(offset)

        items = list(self.db.scalars(statement))
        total = self.db.scalar(count_statement) or 0
        return items, total

    def list_all_for_user(
        self,
        *,
        user_id: uuid.UUID,
        category_type: CategoryType | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[Category]:
        statement: Select[tuple[Category]] = select(Category).where(Category.user_id == user_id)

        if category_type is not None:
            statement = statement.where(Category.type == category_type)

        sort_column = Category.name if sort_by == "name" else Category.created_at
        statement = statement.order_by(
            sort_column.asc() if sort_order == "asc" else sort_column.desc()
        )
        return list(self.db.scalars(statement))

    def get_for_user(self, *, user_id: uuid.UUID, category_id: uuid.UUID) -> Category | None:
        statement = select(Category).where(Category.user_id == user_id, Category.id == category_id)
        return self.db.scalar(statement)

    def find_by_name_for_user(
        self,
        *,
        user_id: uuid.UUID,
        name: str,
        category_type: CategoryType,
    ) -> Category | None:
        statement = select(Category).where(
            Category.user_id == user_id,
            Category.name == name,
            Category.type == category_type,
        )
        return self.db.scalar(statement)

    def create(self, *, user_id: uuid.UUID, payload: dict[str, object]) -> Category:
        category = Category(user_id=user_id, **payload)
        self.db.add(category)
        self.db.flush()
        self.db.refresh(category)
        return category

    def update(self, category: Category, *, payload: dict[str, object]) -> Category:
        for field, value in payload.items():
            setattr(category, field, value)

        self.db.add(category)
        self.db.flush()
        self.db.refresh(category)
        return category

    def delete(self, category: Category) -> None:
        self.db.delete(category)
        self.db.flush()
