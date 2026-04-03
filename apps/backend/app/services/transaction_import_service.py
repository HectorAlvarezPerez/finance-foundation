from __future__ import annotations

import csv
import io
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transactions import (
    TransactionCreate,
    TransactionImportAnalysisResponse,
    TransactionImportColumnMapping,
    TransactionImportCommitRequest,
    TransactionImportCommitResponse,
    TransactionImportDraft,
    TransactionImportPreviewResponse,
)

SUPPORTED_IMPORT_TYPES = {"csv", "xlsx", "xlsm", "xltx", "xltm", "pdf"}
REQUIRED_IMPORT_FIELDS = ("date", "amount", "description")

FIELD_ALIASES = {
    "date": {"date", "fecha", "transactiondate", "bookingdate", "posteddate", "value date"},
    "amount": {"amount", "importe", "total", "value", "sum", "quantity"},
    "description": {
        "description",
        "descripcion",
        "concept",
        "concepto",
        "merchant",
        "payee",
        "beneficiary",
        "details",
    },
    "category": {"category", "categoria"},
    "notes": {"notes", "note", "nota", "comment", "comments", "memo", "reference"},
}


@dataclass
class ParsedImportFile:
    source_type: str
    columns: list[str]
    rows: list[dict[str, str]]
    message: str | None = None


class TransactionImportService:
    def __init__(
        self,
        repository: TransactionRepository,
        account_repository: AccountRepository,
        category_repository: CategoryRepository,
        db: Session,
    ) -> None:
        self.repository = repository
        self.account_repository = account_repository
        self.category_repository = category_repository
        self.db = db

    async def analyze_file(self, *, file: UploadFile) -> TransactionImportAnalysisResponse:
        parsed = await self._parse_upload(file)
        return TransactionImportAnalysisResponse(
            source_type=parsed.source_type,
            columns=parsed.columns,
            sample_rows=parsed.rows[:5],
            suggested_mapping=self._suggest_mapping(parsed.columns),
            total_rows=len(parsed.rows),
            message=parsed.message,
        )

    async def build_preview(
        self,
        *,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        file: UploadFile,
        mapping_json: str,
    ) -> TransactionImportPreviewResponse:
        account = self._require_account(user_id=user_id, account_id=account_id)
        parsed = await self._parse_upload(file)

        if parsed.source_type == "pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF import preview is not available yet in this first iteration",
            )

        mapping = self._parse_mapping(mapping_json)
        self._validate_mapping(mapping)

        categories = self.category_repository.list_all_for_user(
            user_id=user_id,
            sort_by="name",
            sort_order="asc",
        )
        category_by_name = {
            self._normalize_column_name(category.name): category for category in categories
        }

        rows = [
            self._build_draft(
                raw_row=raw_row,
                row_number=index + 1,
                account=account,
                mapping=mapping,
                category_by_name=category_by_name,
            )
            for index, raw_row in enumerate(parsed.rows)
        ]

        return TransactionImportPreviewResponse(
            source_type=parsed.source_type,
            account_id=account.id,
            account_currency=account.currency,
            imported_count=len(rows),
            rows=rows,
        )

    def commit_import(
        self,
        *,
        user_id: uuid.UUID,
        payload: TransactionImportCommitRequest,
    ) -> TransactionImportCommitResponse:
        for item in payload.items:
            account = self._require_account(user_id=user_id, account_id=item.account_id)
            category = self._require_category_if_present(
                user_id=user_id,
                category_id=item.category_id,
            )
            if item.currency != account.currency:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Transaction currency must match the selected account currency",
                )
            if category is not None:
                # Category compatibility is intentionally permissive in this v1.
                pass

            create_payload = TransactionCreate(
                account_id=item.account_id,
                category_id=item.category_id,
                date=item.date,
                amount=item.amount,
                currency=item.currency,
                description=item.description,
                notes=item.notes,
            )
            self.repository.create(user_id=user_id, payload=create_payload.model_dump())

        self.db.commit()
        return TransactionImportCommitResponse(imported_count=len(payload.items))

    async def _parse_upload(self, file: UploadFile) -> ParsedImportFile:
        extension = Path(file.filename or "").suffix.lower().lstrip(".")
        if extension not in SUPPORTED_IMPORT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supported import formats are CSV, Excel and PDF",
            )

        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty",
            )

        if extension == "csv":
            return self._parse_csv(content)
        if extension in {"xlsx", "xlsm", "xltx", "xltm"}:
            return self._parse_excel(content)
        return ParsedImportFile(
            source_type="pdf",
            columns=[],
            rows=[],
            message=(
                "PDF support will use a different extraction path and is not included "
                "in this first iteration"
            ),
        )

    def _parse_csv(self, content: bytes) -> ParsedImportFile:
        text = content.decode("utf-8-sig")
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        columns = [
            column.strip() for column in (reader.fieldnames or []) if column and column.strip()
        ]
        rows = []
        for row in reader:
            normalized = {
                key.strip(): (value.strip() if isinstance(value, str) else "")
                for key, value in row.items()
                if key and key.strip()
            }
            if any(value for value in normalized.values()):
                rows.append(normalized)

        return ParsedImportFile(source_type="csv", columns=columns, rows=rows)

    def _parse_excel(self, content: bytes) -> ParsedImportFile:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        if sheet is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded spreadsheet does not contain a readable sheet",
            )
        rows_iter = sheet.iter_rows(values_only=True)

        try:
            header_row = next(rows_iter)
        except StopIteration as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded spreadsheet is empty",
            ) from exc

        columns = [
            str(value).strip() for value in header_row if value is not None and str(value).strip()
        ]
        parsed_rows: list[dict[str, str]] = []
        for raw_row in rows_iter:
            row_map: dict[str, str] = {}
            for index, column in enumerate(columns):
                value = raw_row[index] if index < len(raw_row) else None
                row_map[column] = self._to_cell_string(value)
            if any(value for value in row_map.values()):
                parsed_rows.append(row_map)

        return ParsedImportFile(source_type="excel", columns=columns, rows=parsed_rows)

    def _suggest_mapping(self, columns: list[str]) -> TransactionImportColumnMapping:
        suggestions: dict[str, str | None] = {field: None for field in FIELD_ALIASES}

        for column in columns:
            normalized_column = self._normalize_column_name(column)
            for field, aliases in FIELD_ALIASES.items():
                if suggestions[field] is None and normalized_column in aliases:
                    suggestions[field] = column

        return TransactionImportColumnMapping(**suggestions)

    def _parse_mapping(self, raw_mapping: str) -> TransactionImportColumnMapping:
        try:
            payload = json.loads(raw_mapping)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Import mapping is not valid JSON",
            ) from exc

        try:
            return TransactionImportColumnMapping.model_validate(payload)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Import mapping is invalid",
            ) from exc

    def _validate_mapping(self, mapping: TransactionImportColumnMapping) -> None:
        missing_fields = [field for field in REQUIRED_IMPORT_FIELDS if not getattr(mapping, field)]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required import fields: {', '.join(missing_fields)}",
            )

    def _build_draft(
        self,
        *,
        raw_row: dict[str, str],
        row_number: int,
        account: Account,
        mapping: TransactionImportColumnMapping,
        category_by_name: dict[str, Category],
    ) -> TransactionImportDraft:
        description_raw = self._mapped_value(raw_row, mapping.description)
        notes_raw = self._mapped_value(raw_row, mapping.notes)
        category_raw = self._mapped_value(raw_row, mapping.category)

        parsed_date = self._parse_date(self._mapped_value(raw_row, mapping.date))
        parsed_amount = self._parse_amount(self._mapped_value(raw_row, mapping.amount))

        validation_errors: list[str] = []
        if parsed_date is None:
            validation_errors.append("Review the date")
        if parsed_amount is None:
            validation_errors.append("Review the amount")
        if not description_raw:
            validation_errors.append("Review the description")

        matched_category = (
            category_by_name.get(self._normalize_column_name(category_raw))
            if category_raw
            else None
        )

        return TransactionImportDraft(
            source_row_number=row_number,
            account_id=account.id,
            category_id=matched_category.id if matched_category else None,
            category_label=category_raw or None,
            date=parsed_date,
            amount=parsed_amount,
            currency=account.currency,
            description=description_raw or None,
            notes=notes_raw or None,
            validation_errors=validation_errors,
        )

    def _mapped_value(self, row: dict[str, str], column_name: str | None) -> str:
        if not column_name:
            return ""
        return (row.get(column_name) or "").strip()

    def _parse_date(self, value: str) -> date | None:
        if not value:
            return None

        cleaned = value.strip()
        for parser in (
            lambda current: date.fromisoformat(current),
            lambda current: datetime.strptime(current, "%d/%m/%Y").date(),
            lambda current: datetime.strptime(current, "%m/%d/%Y").date(),
            lambda current: datetime.strptime(current, "%d-%m-%Y").date(),
        ):
            try:
                return parser(cleaned)
            except ValueError:
                continue

        try:
            excel_serial = float(cleaned)
            excel_base = datetime(1899, 12, 30, tzinfo=UTC)
            return (excel_base + timedelta(days=excel_serial)).date()
        except (ValueError, OverflowError):
            return None

    def _parse_amount(self, value: str) -> Decimal | None:
        if not value:
            return None

        cleaned = value.strip().replace(" ", "")
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")

        cleaned = cleaned.replace("€", "").replace("$", "").replace("£", "")

        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    def _normalize_column_name(self, value: str) -> str:
        return "".join(char for char in value.strip().lower() if char.isalnum())

    def _to_cell_string(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return str(value).strip()

    def _require_account(self, *, user_id: uuid.UUID, account_id: uuid.UUID) -> Account:
        account = self.account_repository.get_for_user(user_id=user_id, account_id=account_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected account does not exist for the current user",
            )
        return account

    def _require_category_if_present(
        self,
        *,
        user_id: uuid.UUID,
        category_id: uuid.UUID | None,
    ) -> Category | None:
        if category_id is None:
            return None

        category = self.category_repository.get_for_user(user_id=user_id, category_id=category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected category does not exist for the current user",
            )
        return category
