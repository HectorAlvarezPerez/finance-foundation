import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BudgetPeriodType
from app.schemas.common import ORMBaseModel


class BudgetBase(BaseModel):
    category_id: uuid.UUID
    period_type: BudgetPeriodType = BudgetPeriodType.MONTHLY
    currency: str = Field(min_length=3, max_length=3)
    amount: Decimal = Field(decimal_places=2, max_digits=12)


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    period_type: BudgetPeriodType | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    amount: Decimal | None = Field(default=None, decimal_places=2, max_digits=12)


class BudgetRead(ORMBaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    period_type: BudgetPeriodType
    currency: str
    amount: Decimal
    position: int
    created_at: datetime
    updated_at: datetime


class BudgetListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[BudgetRead]
    total: int
    limit: int
    offset: int


class BudgetBatchDeleteRequest(BaseModel):
    budget_ids: list[uuid.UUID] = Field(min_length=1)


class BudgetReorderRequest(BaseModel):
    budget_ids: list[uuid.UUID] = Field(min_length=1)


class BudgetBatchDeleteResponse(BaseModel):
    deleted_count: int


class BudgetSpendItem(BaseModel):
    category_id: uuid.UUID
    month: int = Field(ge=1, le=12)
    spent: Decimal


class BudgetSpendResponse(BaseModel):
    year: int
    items: list[BudgetSpendItem]
