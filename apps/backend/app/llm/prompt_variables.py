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


def build_monthly_recap_variables(
    *,
    month_label: str,
    signals_payload: dict[str, Any],
    stories_payload: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "month_label": month_label,
        "signals_payload": json.dumps(signals_payload, ensure_ascii=False),
        "stories_payload": json.dumps(stories_payload, ensure_ascii=False),
    }
