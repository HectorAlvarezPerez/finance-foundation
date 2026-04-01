from __future__ import annotations

import uuid
from datetime import date as date_value
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ORMBaseModel


class TransactionBase(BaseModel):
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    date: date_value
    amount: Decimal = Field(decimal_places=2, max_digits=12)
    currency: str = Field(min_length=3, max_length=3)
    description: str = Field(min_length=1, max_length=512)
    notes: str | None = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    date: date_value | None = None
    amount: Decimal | None = Field(default=None, decimal_places=2, max_digits=12)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    description: str | None = Field(default=None, min_length=1, max_length=512)
    notes: str | None = None


class TransactionRead(ORMBaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    category_id: uuid.UUID | None
    date: date_value
    amount: Decimal
    currency: str
    description: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[TransactionRead]
    total: int
    limit: int
    offset: int
