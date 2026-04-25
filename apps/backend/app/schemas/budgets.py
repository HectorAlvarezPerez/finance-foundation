import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import BudgetPeriodType
from app.schemas.common import ORMBaseModel


class BudgetBase(BaseModel):
    category_id: uuid.UUID
    year: int = Field(ge=2000, le=2100)
    period_type: BudgetPeriodType = BudgetPeriodType.MONTHLY
    month: int | None = Field(default=None, ge=1, le=12)
    currency: str = Field(min_length=3, max_length=3)
    amount: Decimal = Field(decimal_places=2, max_digits=12)

    @model_validator(mode="after")
    def validate_period(self) -> "BudgetBase":
        if self.period_type == BudgetPeriodType.MONTHLY and self.month is None:
            raise ValueError("Month is required for monthly budgets")
        if self.period_type == BudgetPeriodType.ANNUAL and self.month is not None:
            raise ValueError("Month must be empty for annual budgets")
        return self


class BudgetCreate(BudgetBase):
    pass


class BudgetBulkCreate(BaseModel):
    category_id: uuid.UUID
    year: int = Field(ge=2000, le=2100)
    months: list[int] = Field(min_length=1, max_length=12)
    currency: str = Field(min_length=3, max_length=3)
    amount: Decimal = Field(decimal_places=2, max_digits=12)

    @model_validator(mode="after")
    def validate_months(self) -> "BudgetBulkCreate":
        normalized_months = sorted(set(self.months))
        if any(month < 1 or month > 12 for month in normalized_months):
            raise ValueError("Months must be between 1 and 12")
        self.months = normalized_months
        return self


class BudgetUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    year: int | None = Field(default=None, ge=2000, le=2100)
    period_type: BudgetPeriodType | None = None
    month: int | None = Field(default=None, ge=1, le=12)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    amount: Decimal | None = Field(default=None, decimal_places=2, max_digits=12)

    @model_validator(mode="after")
    def validate_period(self) -> "BudgetUpdate":
        if self.period_type == BudgetPeriodType.ANNUAL and self.month is not None:
            raise ValueError("Month must be empty for annual budgets")
        return self


class BudgetRead(ORMBaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    year: int
    period_type: BudgetPeriodType
    month: int | None
    currency: str
    amount: Decimal
    created_at: datetime
    updated_at: datetime


class BudgetListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[BudgetRead]
    total: int
    limit: int
    offset: int


class BudgetBulkCreateResponse(BaseModel):
    items: list[BudgetRead]
    created_count: int
