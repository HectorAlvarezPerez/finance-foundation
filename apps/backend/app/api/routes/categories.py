import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import CurrentUserId, DBSession
from app.models.enums import CategoryType
from app.repositories.category_repository import CategoryRepository
from app.schemas.categories import (
    CategoryCreate,
    CategoryListResponse,
    CategoryRead,
    CategoryUpdate,
)
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


def get_category_service(db: DBSession) -> CategoryService:
    return CategoryService(CategoryRepository(db), db)


CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]


@router.get("", response_model=CategoryListResponse)
def list_categories(
    user_id: CurrentUserId,
    service: CategoryServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category_type: CategoryType | None = None,
    sort_by: Literal["created_at", "name"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> CategoryListResponse:
    return service.list_categories(
        user_id=user_id,
        limit=limit,
        offset=offset,
        category_type=category_type,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    user_id: CurrentUserId,
    service: CategoryServiceDep,
) -> CategoryRead:
    category = service.create_category(user_id=user_id, payload=payload)
    return CategoryRead.model_validate(category)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(
    category_id: uuid.UUID,
    user_id: CurrentUserId,
    service: CategoryServiceDep,
) -> CategoryRead:
    category = service.get_category(user_id=user_id, category_id=category_id)
    return CategoryRead.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    user_id: CurrentUserId,
    service: CategoryServiceDep,
) -> CategoryRead:
    category = service.update_category(user_id=user_id, category_id=category_id, payload=payload)
    return CategoryRead.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: uuid.UUID,
    user_id: CurrentUserId,
    service: CategoryServiceDep,
) -> Response:
    service.delete_category(user_id=user_id, category_id=category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
