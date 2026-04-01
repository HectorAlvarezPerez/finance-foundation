import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


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


class InsightsSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    income: Decimal
    expenses: Decimal
    balance: Decimal
    transaction_count: int
    top_categories: list[InsightsTopCategoryRead]
    monthly_comparison: list[InsightsMonthlyBucketRead]
    account_balances: list[InsightsAccountBalanceRead]
