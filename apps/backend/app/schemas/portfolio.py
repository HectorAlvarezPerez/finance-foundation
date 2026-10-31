import uuid
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import AssetType
from app.schemas.common import ORMBaseModel


class HoldingBase(BaseModel):
    asset_name: str = Field(min_length=1, max_length=255)
    asset_symbol: str | None = Field(default=None, max_length=32)
    asset_type: AssetType
    quantity: Decimal = Field(decimal_places=8, max_digits=20)
    average_buy_price: Decimal = Field(decimal_places=4, max_digits=15)
    currency: str = Field(min_length=3, max_length=3)


class HoldingCreate(HoldingBase):
    pass


class HoldingUpdate(BaseModel):
    asset_name: str | None = Field(default=None, min_length=1, max_length=255)
    asset_symbol: str | None = Field(default=None, max_length=32)
    asset_type: AssetType | None = None
    quantity: Decimal | None = Field(default=None, decimal_places=8, max_digits=20)
    average_buy_price: Decimal | None = Field(default=None, decimal_places=4, max_digits=15)
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class HoldingRead(ORMBaseModel):
    id: uuid.UUID
    asset_name: str
    asset_symbol: str | None
    asset_type: AssetType
    quantity: Decimal
    average_buy_price: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime


class HoldingPriceUpdate(BaseModel):
    price: Decimal = Field(decimal_places=4, max_digits=15, gt=0)


class HoldingContributionCreate(BaseModel):
    amount: Decimal = Field(decimal_places=2, max_digits=15, gt=0)
    price: Decimal = Field(decimal_places=4, max_digits=15, gt=0)
    date: date_type = Field(default_factory=date_type.today)


class PortfolioHoldingRead(BaseModel):
    id: uuid.UUID
    asset_name: str
    asset_symbol: str | None
    asset_type: AssetType
    quantity: Decimal
    average_buy_price: Decimal
    currency: str
    invested: Decimal
    current_price: Decimal | None
    current_value: Decimal | None
    unrealized_pnl: Decimal | None
    allocation_pct: float


class PortfolioSummaryRead(BaseModel):
    holdings: list[PortfolioHoldingRead]
    total_invested: Decimal
    total_value: Decimal
    total_unrealized_pnl: Decimal


class HoldingListResponse(BaseModel):
    items: list[HoldingRead]
    total: int
    limit: int
    offset: int


class PriceRefreshItem(BaseModel):
    asset: str
    price: str | None = None
    reason: str | None = None


class PriceRefreshResponse(BaseModel):
    updated: list[PriceRefreshItem]
    failed: list[PriceRefreshItem]
