from __future__ import annotations

import argparse
import json
import uuid
from types import SimpleNamespace
from typing import Any, cast

from app.core.config import settings
from app.llm.eval_defs import (
    CATEGORY_CLASSIFIER_AGGREGATE_SCORE_NAME,
    CATEGORY_CLASSIFIER_CATEGORY_ACCURACY_SCORE_NAME,
    CATEGORY_CLASSIFIER_DECISION_QUALITY_SCORE_NAME,
    CATEGORY_CLASSIFIER_NULL_BEHAVIOR_SCORE_NAME,
    CATEGORY_CLASSIFIER_TYPE_GUARDRAIL_SCORE_NAME,
    DATASET_PROMOTION_THRESHOLDS,
    PDF_PARSER_AGGREGATE_SCORE_NAME,
    PDF_PARSER_AMOUNT_ACCURACY_SCORE_NAME,
    PDF_PARSER_DATASET_NAME,
    PDF_PARSER_DATE_ACCURACY_SCORE_NAME,
    PDF_PARSER_DESCRIPTION_ACCURACY_SCORE_NAME,
    PDF_PARSER_ROW_PRECISION_SCORE_NAME,
    PDF_PARSER_ROW_RECALL_SCORE_NAME,
)
from app.llm.evals.cases import DATASET_DEFINITIONS
from app.llm.evals.scorers import (
    score_category_classifier_case,
    score_pdf_parser_case,
)
from app.llm.runtime import build_observability_client
from app.models.enums import CategoryType
from app.schemas.transactions import TransactionCategoryAssistantDraft
from app.services.azure_openai_pdf_parser_service import AzureOpenAIPdfParserService
from app.services.azure_openai_transaction_category_service import (
    AzureOpenAITransactionCategoryService,
)


def evaluate_pdf_case(case: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    if dry_run or not settings.azure_openai_pdf_parser_enabled:
        return case["expected_output"]

    service = AzureOpenAIPdfParserService()
    transactions = service.parse_transactions(**case["input"])
    return {"transactions": transactions}


def evaluate_category_case(case: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    if dry_run or not settings.azure_openai_transaction_category_enabled:
        return {
            "category_name": case["expected_output"].get("category_name"),
            "category_type": case["metadata"].get("expected_type"),
            "confidence": 1.0 if case["expected_output"].get("category_name") is not None else None,
        }

    service = AzureOpenAITransactionCategoryService()
    rows = [TransactionCategoryAssistantDraft.model_validate(row) for row in case["input"]["rows"]]
    categories = [
        SimpleNamespace(
            id=uuid.uuid4(),
            name=category["name"],
            type=CategoryType(category["type"]),
        )
        for category in case["input"]["categories"]
    ]
    suggestions = service.classify_rows(rows=rows, categories=cast(Any, categories))
    if not suggestions or suggestions[0].category_id is None:
        return {"category_name": None, "category_type": None, "confidence": None}
    category_by_id = {
        category.id: {
            "name": category.name,
            "type": category.type.value,
        }
        for category in categories
    }
    matched_category = category_by_id.get(suggestions[0].category_id)
    return {
        "category_name": matched_category["name"] if matched_category else None,
        "category_type": matched_category["type"] if matched_category else None,
        "confidence": suggestions[0].confidence,
    }


def _score_name_mapping(dataset_name: str) -> dict[str, str]:
    if dataset_name == PDF_PARSER_DATASET_NAME:
        return {
            "row_recall": PDF_PARSER_ROW_RECALL_SCORE_NAME,
            "row_precision": PDF_PARSER_ROW_PRECISION_SCORE_NAME,
            "amount_accuracy": PDF_PARSER_AMOUNT_ACCURACY_SCORE_NAME,
            "date_accuracy": PDF_PARSER_DATE_ACCURACY_SCORE_NAME,
            "description_accuracy": PDF_PARSER_DESCRIPTION_ACCURACY_SCORE_NAME,
            "aggregate": PDF_PARSER_AGGREGATE_SCORE_NAME,
        }
    return {
        "category_accuracy": CATEGORY_CLASSIFIER_CATEGORY_ACCURACY_SCORE_NAME,
        "null_behavior": CATEGORY_CLASSIFIER_NULL_BEHAVIOR_SCORE_NAME,
        "type_guardrail": CATEGORY_CLASSIFIER_TYPE_GUARDRAIL_SCORE_NAME,
        "decision_quality": CATEGORY_CLASSIFIER_DECISION_QUALITY_SCORE_NAME,
        "aggregate": CATEGORY_CLASSIFIER_AGGREGATE_SCORE_NAME,
    }


def summarize_dataset_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "case_count": 0,
            "metric_averages": {},
            "tag_breakdown": {},
            "promotion_gate": {"passed": False, "checks": {}},
        }

    metric_names = list(results[0]["scores"])
    metric_averages = {
        metric_name: round(
            sum(float(item["scores"][metric_name]) for item in results) / len(results),
            2,
        )
        for metric_name in metric_names
    }

    tag_breakdown: dict[str, dict[str, Any]] = {}
    for item in results:
        for tag in item.get("case_tags", []):
            bucket = tag_breakdown.setdefault(
                tag,
                {"case_count": 0, "aggregate_average": 0.0},
            )
            bucket["case_count"] += 1
            bucket["aggregate_average"] += float(item["scores"]["aggregate"])

    for bucket in tag_breakdown.values():
        bucket["aggregate_average"] = round(
            bucket["aggregate_average"] / bucket["case_count"],
            2,
        )

    aggregate_summary = {
        "case_count": len(results),
        "metric_averages": metric_averages,
        "tag_breakdown": tag_breakdown,
    }
    return aggregate_summary


def build_promotion_gate(dataset_name: str, summary: dict[str, Any]) -> dict[str, Any]:
    thresholds = DATASET_PROMOTION_THRESHOLDS.get(dataset_name, {})
    metric_averages = summary.get("metric_averages", {})
    checks = {
        metric_name: {
            "actual": metric_averages.get(metric_name),
            "threshold": threshold,
            "passed": metric_averages.get(metric_name, 0.0) >= threshold,
        }
        for metric_name, threshold in thresholds.items()
    }
    return {
        "passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
    }


def run_dataset(
    dataset_name: str,
    *,
    dry_run: bool,
) -> list[dict[str, Any]]:
    observability_client = build_observability_client()
    dataset = DATASET_DEFINITIONS[dataset_name]
    results: list[dict[str, Any]] = []
    for case in dataset["items"]:
        case_tags = case["metadata"].get("case_tags", [])
        flow = observability_client.start_flow(
            f"langfuse_eval_{dataset_name}",
            input_payload=case["input"],
            metadata={
                "dataset_name": dataset_name,
                "case_name": case["name"],
                "case_tags": case_tags,
            },
        )
        if dataset_name == PDF_PARSER_DATASET_NAME:
            actual = evaluate_pdf_case(case, dry_run=dry_run)
            scores = score_pdf_parser_case(
                actual_output=actual,
                expected_output=case["expected_output"],
            )
        else:
            actual = evaluate_category_case(case, dry_run=dry_run)
            category_expected = {
                **case["expected_output"],
                "expected_type": case["metadata"].get("expected_type"),
            }
            scores = score_category_classifier_case(
                actual_output=actual,
                expected_output=category_expected,
            )

        score_name_mapping = _score_name_mapping(dataset_name)
        for score_key, score_value in scores.items():
            observability_client.record_score(
                handle=flow,
                name=score_name_mapping[score_key],
                value=score_value,
                comment=case["name"],
                metadata={
                    "dataset_name": dataset_name,
                    "case_name": case["name"],
                    "case_tags": case_tags,
                    "metric_key": score_key,
                },
            )
        observability_client.end_flow(
            flow,
            output_payload={"actual": actual, "expected": case["expected_output"]},
            metadata={
                "scores": scores,
                "case_tags": case_tags,
            },
        )
        results.append(
            {
                "case_name": case["name"],
                "score": scores["aggregate"],
                "scores": scores,
                "actual": actual,
                "case_tags": case_tags,
            }
        )

    observability_client.flush()
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=list(DATASET_DEFINITIONS), default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    dataset_names = [args.dataset] if args.dataset else list(DATASET_DEFINITIONS)
    results = {
        dataset_name: run_dataset(dataset_name, dry_run=args.dry_run)
        for dataset_name in dataset_names
    }
    summaries = {
        dataset_name: summarize_dataset_results(dataset_results)
        for dataset_name, dataset_results in results.items()
    }
    for dataset_name, summary in summaries.items():
        summary["promotion_gate"] = build_promotion_gate(dataset_name, summary)
    print(
        json.dumps(
            {
                "dry_run": args.dry_run,
                "results": results,
                "summaries": summaries,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
