from __future__ import annotations

from typing import Any


def _round_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 2)


def score_pdf_parser_case(
    *,
    actual_output: dict[str, Any],
    expected_output: dict[str, Any],
) -> dict[str, float]:
    actual_transactions = actual_output.get("transactions", [])
    expected_transactions = expected_output.get("transactions", [])
    allow_extra_transactions = bool(expected_output.get("allow_extra_transactions", False))

    if not expected_transactions and not actual_transactions:
        return {
            "row_recall": 1.0,
            "row_precision": 1.0,
            "amount_accuracy": 1.0,
            "date_accuracy": 1.0,
            "description_accuracy": 1.0,
            "aggregate": 1.0,
        }

    matched_actual_indexes: set[int] = set()
    row_matches = 0
    amount_matches = 0
    date_matches = 0
    description_matches = 0

    for expected in expected_transactions:
        for index, actual in enumerate(actual_transactions):
            if index in matched_actual_indexes:
                continue
            if (
                actual.get("Fecha") == expected.get("Fecha")
                and actual.get("Descripción") == expected.get("Descripción")
                and actual.get("Importe") == expected.get("Importe")
            ):
                matched_actual_indexes.add(index)
                row_matches += 1
                amount_matches += 1
                date_matches += 1
                description_matches += 1
                break
        else:
            for index, actual in enumerate(actual_transactions):
                if index in matched_actual_indexes:
                    continue
                if actual.get("Importe") == expected.get("Importe"):
                    amount_matches += 1
                if actual.get("Fecha") == expected.get("Fecha"):
                    date_matches += 1
                if actual.get("Descripción") == expected.get("Descripción"):
                    description_matches += 1
                break

    expected_count = max(len(expected_transactions), 1)
    actual_count = max(len(actual_transactions), 1)
    row_recall = row_matches / expected_count
    if allow_extra_transactions:
        row_precision = 1.0
    else:
        row_precision = row_matches / actual_count if actual_transactions else 0.0
    amount_accuracy = amount_matches / expected_count
    date_accuracy = date_matches / expected_count
    description_accuracy = description_matches / expected_count
    aggregate = (
        (row_recall * 0.35)
        + (row_precision * 0.2)
        + (amount_accuracy * 0.2)
        + (date_accuracy * 0.1)
        + (description_accuracy * 0.15)
    )

    return {
        "row_recall": _round_score(row_recall),
        "row_precision": _round_score(row_precision),
        "amount_accuracy": _round_score(amount_accuracy),
        "date_accuracy": _round_score(date_accuracy),
        "description_accuracy": _round_score(description_accuracy),
        "aggregate": _round_score(aggregate),
    }


def score_category_classifier_case(
    *,
    actual_output: dict[str, Any],
    expected_output: dict[str, Any],
) -> dict[str, float]:
    expected_category_name = expected_output.get("category_name")
    actual_category_name = actual_output.get("category_name")
    expected_type = expected_output.get("expected_type")
    actual_type = actual_output.get("category_type")
    allow_null = bool(expected_output.get("allow_null"))

    category_accuracy = 1.0 if expected_category_name == actual_category_name else 0.0

    if expected_category_name is None:
        null_behavior = 1.0 if actual_category_name is None else 0.0
    elif actual_category_name is None:
        null_behavior = 0.5 if allow_null else 0.0
    else:
        null_behavior = 1.0

    if actual_category_name is None:
        type_guardrail = 1.0 if allow_null else 0.5
    elif expected_type is None or actual_type == expected_type:
        type_guardrail = 1.0
    else:
        type_guardrail = 0.0

    if category_accuracy == 1.0:
        decision_quality = 1.0
    elif expected_category_name is None and actual_category_name is None:
        decision_quality = 1.0
    elif actual_category_name is None:
        decision_quality = 0.5 if allow_null else 0.0
    elif actual_type == expected_type:
        decision_quality = 0.25
    else:
        decision_quality = 0.0

    aggregate = (
        (category_accuracy * 0.4)
        + (null_behavior * 0.2)
        + (type_guardrail * 0.2)
        + (decision_quality * 0.2)
    )

    return {
        "category_accuracy": _round_score(category_accuracy),
        "null_behavior": _round_score(null_behavior),
        "type_guardrail": _round_score(type_guardrail),
        "decision_quality": _round_score(decision_quality),
        "aggregate": _round_score(aggregate),
    }
