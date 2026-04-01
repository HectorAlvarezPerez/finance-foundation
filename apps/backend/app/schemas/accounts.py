import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AccountType
from app.schemas.common import ORMBaseModel


class AccountBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    bank_name: str | None = Field(default=None, min_length=1, max_length=255)
    type: AccountType
    currency: str = Field(min_length=3, max_length=3)


class AccountCreate(AccountBase):
    initial_balance: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=12)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    bank_name: str | None = Field(default=None, min_length=1, max_length=255)
    type: AccountType | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class AccountRead(ORMBaseModel):
    id: uuid.UUID
    name: str
    bank_name: str | None
    type: AccountType
    currency: str
    created_at: datetime
    updated_at: datetime


class AccountListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[AccountRead]
    total: int
    limit: int
    offset: int
