from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
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
from app.services.azure_document_intelligence_ocr_service import (
    AzureDocumentIntelligenceOcrService,
)
from app.services.azure_openai_pdf_parser_service import AzureOpenAIPdfParserService

SUPPORTED_IMPORT_TYPES = {"csv", "xlsx", "xlsm", "xltx", "xltm", "pdf"}
REQUIRED_IMPORT_FIELDS = ("date", "amount", "description")
PDF_EXTRACTED_COLUMNS = ["Fecha", "Descripción", "Importe"]

FIELD_ALIASES = {
    "date": {
        "date",
        "fecha",
        "fechainicio",
        "fechadeinicio",
        "startdate",
        "transactiondate",
        "bookingdate",
        "posteddate",
        "valuedate",
    },
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
        document_ocr_service: AzureDocumentIntelligenceOcrService | None = None,
        pdf_llm_parser_service: AzureOpenAIPdfParserService | None = None,
    ) -> None:
        self.repository = repository
        self.account_repository = account_repository
        self.category_repository = category_repository
        self.db = db
        self.document_ocr_service = document_ocr_service or AzureDocumentIntelligenceOcrService()
        self.pdf_llm_parser_service = pdf_llm_parser_service or AzureOpenAIPdfParserService()

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

        mapping = self._build_effective_mapping(parsed.source_type, mapping_json)
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
        return self._parse_pdf(content)

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

    def _parse_pdf(self, content: bytes) -> ParsedImportFile:
        ocr_result = self.document_ocr_service.extract_text(content=content)
        rows = self._extract_rows_from_pdf_structured_text(ocr_result.structured_text)
        if rows:
            return ParsedImportFile(
                source_type="pdf",
                columns=PDF_EXTRACTED_COLUMNS,
                rows=rows,
                message=(
                    "Hemos leído el PDF con OCR, generado un texto estructurado y preparado "
                    "una propuesta de transacciones. Revísala antes de confirmar la importación."
                ),
            )

        llm_rows = self.pdf_llm_parser_service.parse_transactions(
            structured_text=ocr_result.structured_text,
            tables_markdown=ocr_result.tables_markdown,
        )
        if llm_rows:
            return ParsedImportFile(
                source_type="pdf",
                columns=PDF_EXTRACTED_COLUMNS,
                rows=llm_rows,
                message=(
                    "Hemos leído el PDF con OCR y usado una capa asistida para interpretar "
                    "las transacciones antes de la revisión manual."
                ),
            )

        return ParsedImportFile(
            source_type="pdf",
            columns=PDF_EXTRACTED_COLUMNS,
            rows=[],
            message=(
                "Hemos leído el PDF con OCR, pero no hemos podido convertirlo en movimientos "
                "revisables todavía. Prueba con otro extracto o utiliza CSV/Excel."
            ),
        )

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

    def _build_effective_mapping(
        self,
        source_type: str,
        raw_mapping: str,
    ) -> TransactionImportColumnMapping:
        if source_type != "pdf":
            return self._parse_mapping(raw_mapping)

        return TransactionImportColumnMapping(
            date="Fecha",
            amount="Importe",
            description="Descripción",
            category=None,
            notes=None,
        )

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

    def _extract_rows_from_pdf_structured_text(self, structured_text: str) -> list[dict[str, str]]:
        table_blocks = re.findall(
            r"\[Table \d+\]\n((?:\|.*\|\n?)*)",
            structured_text,
            flags=re.MULTILINE,
        )
        rows: list[dict[str, str]] = []
        for block in table_blocks:
            grid = self._markdown_table_to_grid(block)
            if not self._grid_looks_like_transaction_table(grid):
                continue
            rows.extend(self._transaction_rows_from_grid(grid))
        return rows

    def _markdown_table_to_grid(self, markdown_table: str) -> list[list[str]]:
        rows: list[list[str]] = []
        for raw_line in markdown_table.splitlines():
            line = raw_line.strip()
            if not line.startswith("|") or not line.endswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if cells and all(set(cell) <= {"-"} for cell in cells if cell):
                continue
            rows.append(cells)
        return rows

    def _grid_looks_like_transaction_table(self, grid: list[list[str]]) -> bool:
        if len(grid) < 2:
            return False
        headers = [self._normalize_column_name(value) for value in grid[0]]
        has_date = any("fecha" in header for header in headers)
        has_description = any("descripcion" in header for header in headers)
        has_money = any(
            "dinerosaliente" in header or "dineroentrante" in header or "importe" in header
            for header in headers
        )
        return has_date and has_description and has_money

    def _transaction_rows_from_grid(self, grid: list[list[str]]) -> list[dict[str, str]]:
        header_map = {
            self._normalize_column_name(value): index
            for index, value in enumerate(grid[0])
            if value.strip()
        }

        transaction_date_index = self._find_header_index(
            header_map,
            "fechadelatransaccion",
            "fecha",
        )
        description_index = self._find_header_index(header_map, "descripcion")
        outgoing_index = self._find_header_index(header_map, "dinerosaliente", "importe")
        incoming_index = self._find_header_index(header_map, "dineroentrante")

        if transaction_date_index is None or description_index is None:
            return []

        rows: list[dict[str, str]] = []
        for raw_row in grid[1:]:
            transaction_date = self._table_value(raw_row, transaction_date_index)
            description = self._table_value(raw_row, description_index)
            outgoing = self._table_value(raw_row, outgoing_index)
            incoming = self._table_value(raw_row, incoming_index)
            amount = self._signed_amount_from_columns(outgoing=outgoing, incoming=incoming)

            if not transaction_date or not description or not amount:
                continue

            rows.append(
                {
                    "Fecha": transaction_date,
                    "Descripción": description,
                    "Importe": amount,
                }
            )

        return rows

    def _find_header_index(self, header_map: dict[str, int], *candidates: str) -> int | None:
        for candidate in candidates:
            if candidate in header_map:
                return header_map[candidate]
        return None

    def _table_value(self, row: list[str], index: int | None) -> str:
        if index is None or index >= len(row):
            return ""
        return row[index].strip()

    def _signed_amount_from_columns(self, *, outgoing: str, incoming: str) -> str:
        if outgoing:
            return self._ensure_amount_sign(outgoing, negative=True)
        if incoming:
            return self._ensure_amount_sign(incoming, negative=False)
        return ""

    def _ensure_amount_sign(self, value: str, *, negative: bool) -> str:
        cleaned = value.strip()
        if not cleaned:
            return ""
        if negative and not cleaned.startswith("-"):
            return f"-{cleaned.lstrip('+')}"
        if not negative and cleaned.startswith("-"):
            return cleaned.lstrip("-")
        return cleaned.lstrip("+")

    def _mapped_value(self, row: dict[str, str], column_name: str | None) -> str:
        if not column_name:
            return ""
        return (row.get(column_name) or "").strip()

    def _parse_date(self, value: str) -> date | None:
        if not value:
            return None

        cleaned = self._normalize_human_date(value.strip())
        for parser in (
            lambda current: date.fromisoformat(current),
            lambda current: datetime.fromisoformat(current.replace("Z", "+00:00")).date(),
            lambda current: datetime.strptime(current, "%d %m %Y").date(),
            lambda current: datetime.strptime(current, "%d/%m/%Y").date(),
            lambda current: datetime.strptime(current, "%d/%m/%Y %H:%M:%S").date(),
            lambda current: datetime.strptime(current, "%d/%m/%Y %H:%M").date(),
            lambda current: datetime.strptime(current, "%m/%d/%Y").date(),
            lambda current: datetime.strptime(current, "%m/%d/%Y %H:%M:%S").date(),
            lambda current: datetime.strptime(current, "%m/%d/%Y %H:%M").date(),
            lambda current: datetime.strptime(current, "%d-%m-%Y").date(),
            lambda current: datetime.strptime(current, "%d-%m-%Y %H:%M:%S").date(),
            lambda current: datetime.strptime(current, "%d-%m-%Y %H:%M").date(),
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

    def _normalize_human_date(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value.strip().lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        month_aliases = {
            "ene": "01",
            "enero": "01",
            "feb": "02",
            "febrero": "02",
            "mar": "03",
            "marzo": "03",
            "abr": "04",
            "abril": "04",
            "may": "05",
            "mayo": "05",
            "jun": "06",
            "junio": "06",
            "jul": "07",
            "julio": "07",
            "ago": "08",
            "agosto": "08",
            "sep": "09",
            "sept": "09",
            "septiembre": "09",
            "oct": "10",
            "octubre": "10",
            "nov": "11",
            "noviembre": "11",
            "dic": "12",
            "diciembre": "12",
        }
        match = re.fullmatch(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", normalized)
        if match:
            day, month_label, year = match.groups()
            month_number = month_aliases.get(month_label)
            if month_number:
                return f"{int(day):02d} {month_number} {year}"
        return value.strip()

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
        normalized = unicodedata.normalize("NFKD", value.strip().lower())
        return "".join(
            char for char in normalized if char.isalnum() and not unicodedata.combining(char)
        )

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
