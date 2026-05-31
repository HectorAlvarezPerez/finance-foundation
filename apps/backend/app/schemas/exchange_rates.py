import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel


class ExchangeRateCreate(BaseModel):
    from_currency: str = Field(min_length=3, max_length=3)
    to_currency: str = Field(min_length=3, max_length=3)
    rate: Decimal = Field(decimal_places=10, max_digits=20, gt=0)


class ExchangeRateRead(ORMBaseModel):
    id: uuid.UUID
    from_currency: str
    to_currency: str
    rate: Decimal
    as_of: datetime
    created_at: datetime
    updated_at: datetime


class ExchangeRateListResponse(BaseModel):
    items: list[ExchangeRateRead]
    total: int
