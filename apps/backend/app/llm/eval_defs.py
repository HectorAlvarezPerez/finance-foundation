PDF_TRANSACTION_PARSER_PROMPT_NAME = "pdf-transaction-parser"
TRANSACTION_CATEGORY_ASSISTANT_PROMPT_NAME = "transaction-category-assistant"

PDF_PARSER_DATASET_NAME = "pdf-transaction-parser-v1"
CATEGORY_CLASSIFIER_DATASET_NAME = "transaction-category-assistant-v1"

PDF_PARSER_AGGREGATE_SCORE_NAME = "pdf_parser_match"
PDF_PARSER_ROW_RECALL_SCORE_NAME = "pdf_parser_row_recall"
PDF_PARSER_ROW_PRECISION_SCORE_NAME = "pdf_parser_row_precision"
PDF_PARSER_AMOUNT_ACCURACY_SCORE_NAME = "pdf_parser_amount_accuracy"
PDF_PARSER_DATE_ACCURACY_SCORE_NAME = "pdf_parser_date_accuracy"
PDF_PARSER_DESCRIPTION_ACCURACY_SCORE_NAME = "pdf_parser_description_accuracy"

CATEGORY_CLASSIFIER_AGGREGATE_SCORE_NAME = "category_classifier_match"
CATEGORY_CLASSIFIER_CATEGORY_ACCURACY_SCORE_NAME = "category_classifier_accuracy"
CATEGORY_CLASSIFIER_NULL_BEHAVIOR_SCORE_NAME = "category_classifier_null_behavior"
CATEGORY_CLASSIFIER_TYPE_GUARDRAIL_SCORE_NAME = "category_classifier_type_guardrail"
CATEGORY_CLASSIFIER_DECISION_QUALITY_SCORE_NAME = "category_classifier_decision_quality"

DATASET_PROMOTION_THRESHOLDS = {
    PDF_PARSER_DATASET_NAME: {
        "aggregate": 0.9,
        "row_recall": 0.95,
        "amount_accuracy": 0.95,
    },
    CATEGORY_CLASSIFIER_DATASET_NAME: {
        "aggregate": 0.9,
        "type_guardrail": 0.95,
        "decision_quality": 0.85,
    },
}
