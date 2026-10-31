import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CategoryType
from app.schemas.common import ORMBaseModel


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: CategoryType
    color: str | None = Field(default=None, max_length=32)
    icon: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: CategoryType | None = None
    color: str | None = Field(default=None, max_length=32)
    icon: str | None = None


class CategoryRead(ORMBaseModel):
    id: uuid.UUID
    name: str
    type: CategoryType
    color: str | None
    icon: str | None
    created_at: datetime
    updated_at: datetime


class CategoryListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[CategoryRead]
    total: int
    limit: int
    offset: int
