from __future__ import annotations

import json
from typing import Any


def build_pdf_parser_variables(*, structured_text: str, tables_markdown: str) -> dict[str, Any]:
    return {
        "structured_text": structured_text,
        "tables_markdown": tables_markdown,
    }


def build_category_classifier_variables(
    *,
    category_payload: list[dict[str, Any]],
    row_payload: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "category_payload": json.dumps(category_payload, ensure_ascii=False),
        "row_payload": json.dumps(row_payload, ensure_ascii=False),
    }
