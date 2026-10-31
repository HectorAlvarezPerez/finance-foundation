from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings

try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
    from azure.core.credentials import AzureKeyCredential
    from azure.core.exceptions import HttpResponseError
except ImportError:  # pragma: no cover - guarded by project dependencies
    DocumentIntelligenceClient = None
    AnalyzeDocumentRequest = None
    AzureKeyCredential = None
    HttpResponseError = Exception


@dataclass
class OcrExtractionResult:
    text: str
    page_count: int
    tables_markdown: str
    structured_text: str
    tables: list["OcrTable"]


@dataclass
class OcrTableCell:
    row_index: int
    column_index: int
    content: str
    kind: str | None = None


@dataclass
class OcrTable:
    row_count: int
    column_count: int
    page_number: int | None
    top: float | None
    bbox: tuple[float, float, float, float] | None
    cells: list[OcrTableCell]


class AzureDocumentIntelligenceOcrService:
    def __init__(self) -> None:
        self.endpoint = settings.azure_document_intelligence_endpoint
        self.api_key = settings.azure_document_intelligence_api_key
        self.model_id = settings.azure_document_intelligence_model_id

    def extract_text(self, *, content: bytes) -> OcrExtractionResult:
        if not settings.azure_document_intelligence_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "PDF import requires Azure Document Intelligence to be configured "
                    "in the backend"
                ),
            )

        if (
            DocumentIntelligenceClient is None
            or AnalyzeDocumentRequest is None
            or AzureKeyCredential is None
        ):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Azure Document Intelligence SDK is not installed in the backend",
            )

        endpoint = self.endpoint
        api_key = self.api_key
        if endpoint is None or api_key is None:  # pragma: no cover - narrowed by guard above
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Azure Document Intelligence credentials are incomplete in the backend",
            )

        client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key),
        )

        try:
            poller = client.begin_analyze_document(
                self.model_id,
                body=AnalyzeDocumentRequest(bytes_source=content),
            )
            result = poller.result()
        except HttpResponseError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Azure Document Intelligence could not analyze the uploaded PDF: {exc}",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unexpected error while processing the uploaded PDF with Azure OCR",
            ) from exc

        extracted_text = self._extract_text_from_result(result)
        if not extracted_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Azure OCR did not return readable text for the uploaded PDF",
            )

        page_count = len(getattr(result, "pages", []) or [])
        tables = self._extract_tables_from_result(result)
        return OcrExtractionResult(
            text=extracted_text,
            page_count=page_count,
            tables_markdown=self._tables_to_markdown(tables),
            structured_text=self._structured_text_from_result(result, tables),
            tables=tables,
        )

    def _extract_text_from_result(self, result: object) -> str:
        content = getattr(result, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()

        pages = getattr(result, "pages", None) or []
        lines: list[str] = []
        for page in pages:
            for line in getattr(page, "lines", None) or []:
                text = getattr(line, "content", None)
                if isinstance(text, str) and text.strip():
                    lines.append(text.strip())
        return "\n".join(lines).strip()

    def _extract_tables_from_result(self, result: object) -> list[OcrTable]:
        tables: list[OcrTable] = []
        for table in getattr(result, "tables", None) or []:
            page_number = None
            top = None
            bbox = None
            for region in getattr(table, "bounding_regions", None) or []:
                page_number = getattr(region, "page_number", None)
                region_bbox = self._polygon_to_bbox(getattr(region, "polygon", None))
                if region_bbox is not None:
                    bbox = region_bbox
                    top = region_bbox[1]
                    break

            cells = [
                OcrTableCell(
                    row_index=getattr(cell, "row_index", 0),
                    column_index=getattr(cell, "column_index", 0),
                    content=(getattr(cell, "content", "") or "").strip(),
                    kind=str(getattr(cell, "kind", "")) if getattr(cell, "kind", None) else None,
                )
                for cell in getattr(table, "cells", None) or []
            ]
            tables.append(
                OcrTable(
                    row_count=getattr(table, "row_count", 0) or 0,
                    column_count=getattr(table, "column_count", 0) or 0,
                    page_number=page_number,
                    top=top,
                    bbox=bbox,
                    cells=cells,
                )
            )
        return tables

    def _tables_to_markdown(self, tables: list[OcrTable]) -> str:
        sections: list[str] = []
        for index, table in enumerate(tables, start=1):
            grid = self._table_to_grid(table)
            sections.append(f"## Table {index}")
            if not grid:
                sections.append("_Empty table_")
                sections.append("")
                continue

            header = grid[0]
            sections.append("| " + " | ".join(header) + " |")
            sections.append("| " + " | ".join(["---"] * len(header)) + " |")
            for row in grid[1:]:
                sections.append("| " + " | ".join(row) + " |")
            sections.append("")
        return "\n".join(sections).strip()

    def _structured_text_from_result(self, result: object, tables: list[OcrTable]) -> str:
        sections: list[str] = []
        for page in getattr(result, "pages", None) or []:
            page_number = getattr(page, "page_number", None)
            page_blocks: list[tuple[float, str]] = []
            page_tables = [table for table in tables if table.page_number == page_number]
            table_bboxes = [(table.top, table) for table in page_tables if table.top is not None]

            previous_top: float | None = None
            paragraph_lines: list[tuple[float, str]] = []
            for line in getattr(page, "lines", None) or []:
                text = (getattr(line, "content", "") or "").strip()
                if not text:
                    continue

                polygon = getattr(line, "polygon", None)
                bbox = self._polygon_to_bbox(polygon)
                top = bbox[1] if bbox is not None else (previous_top or 0.0)
                if self._line_inside_any_table(bbox, page_tables):
                    continue

                if previous_top is not None and abs(top - previous_top) > 0.22 and paragraph_lines:
                    paragraph_text = "\n".join(text for _, text in paragraph_lines)
                    page_blocks.append((paragraph_lines[0][0], paragraph_text))
                    paragraph_lines = []
                paragraph_lines.append((top, text))
                previous_top = top

            if paragraph_lines:
                paragraph_text = "\n".join(text for _, text in paragraph_lines)
                page_blocks.append((paragraph_lines[0][0], paragraph_text))

            for index, (table_top, table) in enumerate(table_bboxes, start=1):
                table_content = self._table_markdown_for_structured_output(table, index, tables)
                page_blocks.append((table_top, table_content))

            page_blocks.sort(key=lambda item: item[0])
            sections.append(f"# Page {page_number}")
            sections.extend(content for _, content in page_blocks)
            sections.append("")

        return "\n\n".join(section for section in sections if section).strip()

    def _table_markdown_for_structured_output(
        self,
        table: OcrTable,
        table_index_on_page: int,
        all_tables: list[OcrTable],
    ) -> str:
        global_index = all_tables.index(table) + 1
        grid = self._table_to_grid(table)
        lines = [f"[Table {global_index}]"]
        if not grid:
            lines.append("(empty table)")
            return "\n".join(lines)

        header = grid[0]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for row in grid[1:]:
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    def _table_to_grid(self, table: OcrTable) -> list[list[str]]:
        grid = [["" for _ in range(table.column_count)] for _ in range(table.row_count)]
        for cell in table.cells:
            if cell.row_index >= table.row_count or cell.column_index >= table.column_count:
                continue
            grid[cell.row_index][cell.column_index] = cell.content.replace("\n", " ").strip()
        return grid

    def _line_inside_any_table(
        self,
        line_bbox: tuple[float, float, float, float] | None,
        page_tables: list[OcrTable],
    ) -> bool:
        if line_bbox is None:
            return False
        line_left, line_top, line_right, line_bottom = line_bbox
        line_center_x = (line_left + line_right) / 2
        line_center_y = (line_top + line_bottom) / 2

        for table in page_tables:
            if table.top is None:
                continue
            region_bbox = table.bbox
            if region_bbox is None:
                continue
            table_left, table_top, table_right, table_bottom = region_bbox
            if (
                table_left <= line_center_x <= table_right
                and table_top <= line_center_y <= table_bottom
            ):
                return True
        return False

    def _polygon_to_bbox(
        self,
        polygon: list[float] | Any | None,
    ) -> tuple[float, float, float, float] | None:
        if not polygon:
            return None
        xs = polygon[0::2]
        ys = polygon[1::2]
        if not xs or not ys:
            return None
        return min(xs), min(ys), max(xs), max(ys)
