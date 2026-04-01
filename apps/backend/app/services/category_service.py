import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import CategoryType
from app.repositories.category_repository import CategoryRepository
from app.schemas.categories import (
    CategoryCreate,
    CategoryListResponse,
    CategoryRead,
    CategoryUpdate,
)


class CategoryService:
    def __init__(self, repository: CategoryRepository, db: Session) -> None:
        self.repository = repository
        self.db = db

    def list_categories(
        self,
        *,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
        category_type: CategoryType | None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> CategoryListResponse:
        items, total = self.repository.list_for_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
            category_type=category_type,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return CategoryListResponse(
            items=[CategoryRead.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_category(self, *, user_id: uuid.UUID, category_id: uuid.UUID) -> Category:
        category = self.repository.get_for_user(user_id=user_id, category_id=category_id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        return category

    def create_category(self, *, user_id: uuid.UUID, payload: CategoryCreate) -> Category:
        duplicate = self.repository.find_by_name_for_user(
            user_id=user_id,
            name=payload.name,
            category_type=payload.type,
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A category with the same name and type already exists",
            )
        category = self.repository.create(user_id=user_id, payload=payload.model_dump())
        self.db.commit()
        return category

    def update_category(
        self,
        *,
        user_id: uuid.UUID,
        category_id: uuid.UUID,
        payload: CategoryUpdate,
    ) -> Category:
        category = self.get_category(user_id=user_id, category_id=category_id)
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return category

        next_name = updates.get("name", category.name)
        next_type = updates.get("type", category.type)
        duplicate = self.repository.find_by_name_for_user(
            user_id=user_id,
            name=next_name,
            category_type=next_type,
        )
        if duplicate is not None and duplicate.id != category.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A category with the same name and type already exists",
            )

        category = self.repository.update(category, payload=updates)
        self.db.commit()
        return category

    def delete_category(self, *, user_id: uuid.UUID, category_id: uuid.UUID) -> None:
        category = self.get_category(user_id=user_id, category_id=category_id)
        try:
            self.repository.delete(category)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category cannot be deleted because it is still referenced",
            ) from exc
