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


class TransactionImportColumnMapping(BaseModel):
    date: str | None = None
    amount: str | None = None
    description: str | None = None
    category: str | None = None
    notes: str | None = None


class TransactionImportAnalysisResponse(BaseModel):
    source_type: str
    columns: list[str]
    sample_rows: list[dict[str, str]]
    suggested_mapping: TransactionImportColumnMapping
    total_rows: int
    message: str | None = None


class TransactionImportDraft(BaseModel):
    source_row_number: int
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    category_label: str | None = None
    date: date_value | None = None
    amount: Decimal | None = Field(default=None, decimal_places=2, max_digits=12)
    currency: str = Field(min_length=3, max_length=3)
    description: str | None = Field(default=None, min_length=1, max_length=512)
    notes: str | None = None
    validation_errors: list[str] = Field(default_factory=list)


class TransactionImportPreviewResponse(BaseModel):
    source_type: str
    account_id: uuid.UUID
    account_currency: str
    imported_count: int
    rows: list[TransactionImportDraft]


class TransactionImportCommitItem(TransactionBase):
    source_row_number: int | None = None


class TransactionImportCommitRequest(BaseModel):
    items: list[TransactionImportCommitItem] = Field(min_length=1, max_length=500)


class TransactionImportCommitResponse(BaseModel):
    imported_count: int


class PdfParsedTransaction(BaseModel):
    date: str = Field(min_length=1)
    description: str = Field(min_length=1, max_length=512)
    amount: str = Field(min_length=1)


class PdfParsedTransactionsResponse(BaseModel):
    transactions: list[PdfParsedTransaction] = Field(default_factory=list)
