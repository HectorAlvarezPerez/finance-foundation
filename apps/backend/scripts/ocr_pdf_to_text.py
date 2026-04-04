from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential

from app.core.config import settings


@dataclass
class PageBlock:
    top: float
    kind: str
    content: str


def build_client() -> DocumentIntelligenceClient:
    if not settings.azure_document_intelligence_enabled:
        raise SystemExit(
            "Azure Document Intelligence is not configured. "
            "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_API_KEY."
        )

    endpoint = settings.azure_document_intelligence_endpoint
    api_key = settings.azure_document_intelligence_api_key
    if endpoint is None or api_key is None:
        raise SystemExit("Azure Document Intelligence credentials are incomplete.")

    return DocumentIntelligenceClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key),
    )


def extract_result(pdf_path: Path, model_id: str) -> Any:
    client = build_client()
    content = pdf_path.read_bytes()
    poller = client.begin_analyze_document(
        model_id,
        body=AnalyzeDocumentRequest(bytes_source=content),
    )
    return poller.result()


def result_to_text(result: Any) -> str:
    content = getattr(result, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()

    lines: list[str] = []
    for page in getattr(result, "pages", None) or []:
        for line in getattr(page, "lines", None) or []:
            value = getattr(line, "content", None)
            if isinstance(value, str) and value.strip():
                lines.append(value.strip())
    return "\n".join(lines).strip()


def result_to_summary(result: Any) -> dict[str, Any]:
    pages_summary: list[dict[str, Any]] = []
    for page in getattr(result, "pages", None) or []:
        page_lines = []
        for line in getattr(page, "lines", None) or []:
            page_lines.append(
                {
                    "content": getattr(line, "content", ""),
                    "polygon": getattr(line, "polygon", None),
                }
            )
        pages_summary.append(
            {
                "page_number": getattr(page, "page_number", None),
                "width": getattr(page, "width", None),
                "height": getattr(page, "height", None),
                "unit": getattr(page, "unit", None),
                "lines": page_lines,
            }
        )

    tables_summary: list[dict[str, Any]] = []
    for table in getattr(result, "tables", None) or []:
        table_cells = []
        for cell in getattr(table, "cells", None) or []:
            table_cells.append(
                {
                    "row_index": getattr(cell, "row_index", None),
                    "column_index": getattr(cell, "column_index", None),
                    "content": getattr(cell, "content", ""),
                    "kind": str(getattr(cell, "kind", "")) if getattr(cell, "kind", None) else None,
                }
            )
        tables_summary.append(
            {
                "row_count": getattr(table, "row_count", None),
                "column_count": getattr(table, "column_count", None),
                "cells": table_cells,
            }
        )

    return {
        "model_id": getattr(result, "model_id", None),
        "content": getattr(result, "content", None),
        "pages": pages_summary,
        "tables": tables_summary,
    }


def result_to_tables_markdown(result: Any) -> str:
    sections: list[str] = []
    for index, table in enumerate(getattr(result, "tables", None) or [], start=1):
        row_count = getattr(table, "row_count", 0) or 0
        column_count = getattr(table, "column_count", 0) or 0
        grid = [["" for _ in range(column_count)] for _ in range(row_count)]

        for cell in getattr(table, "cells", None) or []:
            row_index = getattr(cell, "row_index", None)
            column_index = getattr(cell, "column_index", None)
            if row_index is None or column_index is None:
                continue
            if row_index >= row_count or column_index >= column_count:
                continue
            content = (getattr(cell, "content", "") or "").replace("\n", " ").strip()
            grid[row_index][column_index] = content

        sections.append(f"## Table {index}")
        if not grid:
            sections.append("_Empty table_")
            continue

        header = grid[0]
        sections.append("| " + " | ".join(header) + " |")
        sections.append("| " + " | ".join(["---"] * len(header)) + " |")
        for row in grid[1:]:
            sections.append("| " + " | ".join(row) + " |")
        sections.append("")

    return "\n".join(sections).strip()


def polygon_to_bbox(polygon: list[float] | None) -> tuple[float, float, float, float] | None:
    if not polygon:
        return None

    xs = polygon[0::2]
    ys = polygon[1::2]
    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def line_is_inside_table_bbox(
    line_polygon: list[float] | None,
    table_bboxes: list[tuple[float, float, float, float]],
) -> bool:
    line_bbox = polygon_to_bbox(line_polygon)
    if line_bbox is None:
        return False

    line_left, line_top, line_right, line_bottom = line_bbox
    line_center_y = (line_top + line_bottom) / 2
    line_center_x = (line_left + line_right) / 2

    for table_left, table_top, table_right, table_bottom in table_bboxes:
        if (
            table_left <= line_center_x <= table_right
            and table_top <= line_center_y <= table_bottom
        ):
            return True
    return False


def table_to_grid(table: Any) -> list[list[str]]:
    row_count = getattr(table, "row_count", 0) or 0
    column_count = getattr(table, "column_count", 0) or 0
    grid = [["" for _ in range(column_count)] for _ in range(row_count)]

    for cell in getattr(table, "cells", None) or []:
        row_index = getattr(cell, "row_index", None)
        column_index = getattr(cell, "column_index", None)
        if row_index is None or column_index is None:
            continue
        if row_index >= row_count or column_index >= column_count:
            continue
        content = (getattr(cell, "content", "") or "").replace("\n", " ").strip()
        grid[row_index][column_index] = content

    return grid


def table_to_markdown(table: Any, index: int) -> str:
    grid = table_to_grid(table)
    lines = [f"[Table {index}]"]
    if not grid:
        lines.append("(empty table)")
        return "\n".join(lines)

    header = grid[0]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for row in grid[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def result_to_structured_text(result: Any) -> str:
    sections: list[str] = []
    all_tables = getattr(result, "tables", None) or []

    for page in getattr(result, "pages", None) or []:
        page_number = getattr(page, "page_number", None)
        page_blocks: list[PageBlock] = []
        table_bboxes: list[tuple[float, float, float, float]] = []

        page_tables: list[tuple[int, Any, tuple[float, float, float, float]]] = []
        for table_index, table in enumerate(all_tables, start=1):
            for region in getattr(table, "bounding_regions", None) or []:
                if getattr(region, "page_number", None) != page_number:
                    continue
                bbox = polygon_to_bbox(getattr(region, "polygon", None))
                if bbox is None:
                    continue
                table_bboxes.append(bbox)
                page_tables.append((table_index, table, bbox))

        paragraph_lines: list[tuple[float, str]] = []
        previous_top: float | None = None
        for line in getattr(page, "lines", None) or []:
            content = (getattr(line, "content", "") or "").strip()
            if not content:
                continue
            if line_is_inside_table_bbox(getattr(line, "polygon", None), table_bboxes):
                continue

            bbox = polygon_to_bbox(getattr(line, "polygon", None))
            top = bbox[1] if bbox is not None else (previous_top or 0.0)
            if previous_top is not None and abs(top - previous_top) > 0.22 and paragraph_lines:
                paragraph_text = "\n".join(text for _, text in paragraph_lines)
                page_blocks.append(
                    PageBlock(
                        top=paragraph_lines[0][0],
                        kind="text",
                        content=paragraph_text,
                    )
                )
                paragraph_lines = []

            paragraph_lines.append((top, content))
            previous_top = top

        if paragraph_lines:
            paragraph_text = "\n".join(text for _, text in paragraph_lines)
            page_blocks.append(
                PageBlock(
                    top=paragraph_lines[0][0],
                    kind="text",
                    content=paragraph_text,
                )
            )

        for table_index, table, bbox in page_tables:
            page_blocks.append(
                PageBlock(
                    top=bbox[1],
                    kind="table",
                    content=table_to_markdown(table, table_index),
                )
            )

        page_blocks.sort(key=lambda block: block.top)
        sections.append(f"# Page {page_number}")
        for block in page_blocks:
            sections.append(block.content)
            sections.append("")

    return "\n".join(section for section in sections if section is not None).strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Azure Document Intelligence on a PDF and save OCR outputs.",
    )
    parser.add_argument("pdf_path", help="Absolute or relative path to the PDF file")
    parser.add_argument(
        "--model-id",
        default=settings.azure_document_intelligence_model_id,
        help="Azure Document Intelligence model id to use",
    )
    parser.add_argument(
        "--output-dir",
        default="tmp/ocr-debug",
        help="Directory where the OCR outputs will be written",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path).expanduser().resolve()
    if not pdf_path.exists():
        raise SystemExit(f"PDF file not found: {pdf_path}")

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    result = extract_result(pdf_path, args.model_id)
    extracted_text = result_to_text(result)
    summary = result_to_summary(result)

    txt_path = output_dir / f"{pdf_path.stem}.ocr.txt"
    json_path = output_dir / f"{pdf_path.stem}.ocr.json"
    tables_path = output_dir / f"{pdf_path.stem}.ocr.tables.md"
    structured_path = output_dir / f"{pdf_path.stem}.ocr.structured.txt"

    txt_path.write_text(f"{extracted_text}\n", encoding="utf-8")
    json_path.write_text(f"{json.dumps(summary, indent=2, ensure_ascii=False)}\n", encoding="utf-8")
    tables_path.write_text(f"{result_to_tables_markdown(result)}\n", encoding="utf-8")
    structured_path.write_text(f"{result_to_structured_text(result)}\n", encoding="utf-8")

    print(f"Saved OCR text to: {txt_path}")
    print(f"Saved OCR JSON to: {json_path}")
    print(f"Saved OCR tables to: {tables_path}")
    print(f"Saved OCR structured text to: {structured_path}")
    print(f"Characters extracted: {len(extracted_text)}")


if __name__ == "__main__":
    main()
