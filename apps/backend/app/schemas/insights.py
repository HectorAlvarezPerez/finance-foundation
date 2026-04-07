import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class InsightsTopCategoryRead(BaseModel):
    category_id: uuid.UUID | None
    name: str
    color: str
    total: Decimal


class InsightsMonthlyBucketRead(BaseModel):
    month_key: str
    month_label: str
    income: Decimal
    expenses: Decimal
    net: Decimal
    transactions: int


class InsightsAccountBalanceRead(BaseModel):
    account_id: uuid.UUID
    name: str
    currency: str
    total: Decimal


class InsightsMonthlyRecapMonthRead(BaseModel):
    month_key: str = Field(pattern=r"^\d{4}-\d{2}$")
    month_label: str


class InsightsMonthlyRecapFactRead(BaseModel):
    label: str
    value: str
    tone: Literal["neutral", "positive", "negative", "accent"] = "neutral"


class InsightsMonthlyRecapVisualDatumRead(BaseModel):
    label: str
    value: Decimal | None = None
    color: str | None = None


class InsightsMonthlyRecapVisualRead(BaseModel):
    kind: Literal["top_category", "biggest_moment", "month_comparison"]
    amount: Decimal | None = None
    share: float | None = None
    category_name: str | None = None
    category_color: str | None = None
    series: list[InsightsMonthlyRecapVisualDatumRead] = Field(default_factory=list)
    date_label: str | None = None
    description: str | None = None
    merchant: str | None = None
    accent_color: str | None = None
    current_amount: Decimal | None = None
    previous_amount: Decimal | None = None
    delta: Decimal | None = None
    current_label: str | None = None
    previous_label: str | None = None
    current_color: str | None = None
    previous_color: str | None = None


class InsightsMonthlyRecapStoryRead(BaseModel):
    id: str
    kind: Literal["top_category", "biggest_moment", "month_comparison"]
    theme: Literal["amber", "rose", "sky", "lime", "slate"]
    title: str
    headline: str
    subheadline: str
    body: str
    facts: list[InsightsMonthlyRecapFactRead] = Field(default_factory=list)
    visual: InsightsMonthlyRecapVisualRead


class InsightsMonthlyRecapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    month_key: str = Field(pattern=r"^\d{4}-\d{2}$")
    month_label: str
    status: Literal["ready", "fallback"]
    generated_at: datetime
    is_stale: bool = False
    stories: list[InsightsMonthlyRecapStoryRead] = Field(default_factory=list)


class InsightsMonthlyRecapRegenerateRequest(BaseModel):
    month_key: str = Field(pattern=r"^\d{4}-\d{2}$")


class InsightsSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    income: Decimal
    expenses: Decimal
    balance: Decimal
    transaction_count: int
    top_categories: list[InsightsTopCategoryRead]
    monthly_comparison: list[InsightsMonthlyBucketRead]
    account_balances: list[InsightsAccountBalanceRead]
    available_recap_months: list[InsightsMonthlyRecapMonthRead] = Field(default_factory=list)
