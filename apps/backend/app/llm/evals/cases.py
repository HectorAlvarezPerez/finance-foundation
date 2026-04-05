from __future__ import annotations

from app.llm.eval_defs import (
    CATEGORY_CLASSIFIER_DATASET_NAME,
    PDF_PARSER_DATASET_NAME,
)

PDF_PARSER_CASES = [
    {
        "name": "pdf_parser_structured_table_happy_path",
        "input": {
            "structured_text": (
                "# Page 1\n\n"
                "[Table 4]\n"
                "| Fecha de la transacción | Fecha valor | Descripción | Dinero saliente | "
                "| | Dinero entrante | Saldo |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n"
                "| 1 abr 2026 | 1 abr 2026 | Servei d Activitat Fisica (SAF) | "
                "13,00€ | | | 692,91 |\n"
                "| | | Referencia: QUOTA D'ABONAMENT MES D'ABRIL 2026 | | | | € |\n"
                "| 1 abr 2026 | 2 abr 2026 | Botiga Olot | 4,98€ | | | 687,93 |\n"
            ),
            "tables_markdown": (
                "## Table 4\n"
                "| Fecha de la transacción | Fecha valor | Descripción | Dinero saliente | "
                "| | Dinero entrante | Saldo |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n"
                "| 1 abr 2026 | 1 abr 2026 | Servei d Activitat Fisica (SAF) | "
                "13,00€ | | | 692,91 |\n"
                "| | | Referencia: QUOTA D'ABONAMENT MES D'ABRIL 2026 | | | | € |\n"
                "| 1 abr 2026 | 2 abr 2026 | Botiga Olot | 4,98€ | | | 687,93 |\n"
            ),
        },
        "expected_output": {
            "transactions": [
                {
                    "Fecha": "2026-04-01",
                    "Descripción": "Servei d Activitat Fisica (SAF)",
                    "Importe": "-13.00",
                },
                {
                    "Fecha": "2026-04-01",
                    "Descripción": "Botiga Olot",
                    "Importe": "-4.98",
                },
            ],
            "allow_extra_transactions": False,
        },
        "metadata": {
            "dataset_name": PDF_PARSER_DATASET_NAME,
            "case_tags": ["happy_path", "structured_table"],
        },
    },
    {
        "name": "pdf_parser_ignores_noise_and_footer",
        "input": {
            "structured_text": "# Page 1\nSome OCR with support footer and no transaction rows",
            "tables_markdown": (
                "## Table 1\n| Support | Footer |\n| --- | --- |\n| Help | Legal |\n"
            ),
        },
        "expected_output": {"transactions": [], "allow_extra_transactions": False},
        "metadata": {
            "dataset_name": PDF_PARSER_DATASET_NAME,
            "case_tags": ["noise", "footer_guardrail"],
        },
    },
    {
        "name": "pdf_parser_llm_fallback_case",
        "input": {
            "structured_text": "# Page 1\nSome OCR",
            "tables_markdown": "## Table 1\n| col | col2 |",
        },
        "expected_output": {
            "transactions": [
                {
                    "Fecha": "2026-04-02",
                    "Descripción": "Ametller Origen",
                    "Importe": "-2.09",
                }
            ],
            "allow_extra_transactions": False,
        },
        "metadata": {
            "dataset_name": PDF_PARSER_DATASET_NAME,
            "case_tags": ["fallback", "llm"],
        },
    },
    {
        "name": "pdf_parser_keeps_pending_transaction_rows",
        "input": {
            "structured_text": (
                "# Page 1\n\n"
                "[Table 2]\n"
                "| Fecha | Descripción | Estado | Importe |\n"
                "| --- | --- | --- | --- |\n"
                "| 5 abr 2026 | Pending Spotify Subscription | Pendiente | 9,99€ |\n"
            ),
            "tables_markdown": (
                "## Table 2\n"
                "| Fecha | Descripción | Estado | Importe |\n"
                "| --- | --- | --- | --- |\n"
                "| 5 abr 2026 | Pending Spotify Subscription | Pendiente | 9,99€ |\n"
            ),
        },
        "expected_output": {
            "transactions": [
                {
                    "Fecha": "2026-04-05",
                    "Descripción": "Pending Spotify Subscription",
                    "Importe": "-9.99",
                }
            ],
            "allow_extra_transactions": False,
        },
        "metadata": {
            "dataset_name": PDF_PARSER_DATASET_NAME,
            "case_tags": ["pending", "structured_table"],
        },
    },
    {
        "name": "pdf_parser_handles_incoming_positive_amount",
        "input": {
            "structured_text": (
                "# Page 1\n\n"
                "[Table 3]\n"
                "| Fecha | Descripción | Dinero entrante |\n"
                "| --- | --- | --- |\n"
                "| 6 abr 2026 | Bizum recibido Ana | 25,00€ |\n"
            ),
            "tables_markdown": (
                "## Table 3\n"
                "| Fecha | Descripción | Dinero entrante |\n"
                "| --- | --- | --- |\n"
                "| 6 abr 2026 | Bizum recibido Ana | 25,00€ |\n"
            ),
        },
        "expected_output": {
            "transactions": [
                {
                    "Fecha": "2026-04-06",
                    "Descripción": "Bizum recibido Ana",
                    "Importe": "25.00",
                }
            ],
            "allow_extra_transactions": False,
        },
        "metadata": {
            "dataset_name": PDF_PARSER_DATASET_NAME,
            "case_tags": ["incoming", "sign_guardrail"],
        },
    },
]

CATEGORY_CLASSIFIER_CASES = [
    {
        "name": "category_classifier_groceries_known_merchant",
        "input": {
            "rows": [
                {
                    "source_row_number": 1,
                    "description": "Unknown Corner Shop",
                    "notes": None,
                    "amount": "-9.90",
                    "currency": "EUR",
                }
            ],
            "categories": [
                {"name": "Groceries", "type": "expense"},
                {"name": "Salary", "type": "income"},
                {"name": "Transfer", "type": "transfer"},
            ],
        },
        "expected_output": {"category_name": "Groceries", "allow_null": False},
        "metadata": {
            "dataset_name": CATEGORY_CLASSIFIER_DATASET_NAME,
            "case_tags": ["happy_path", "merchant_match"],
            "expected_type": "expense",
        },
    },
    {
        "name": "category_classifier_income_vs_expense_guardrail",
        "input": {
            "rows": [
                {
                    "source_row_number": 1,
                    "description": "Monthly payroll payment",
                    "notes": None,
                    "amount": "2500.00",
                    "currency": "EUR",
                }
            ],
            "categories": [
                {"name": "Groceries", "type": "expense"},
                {"name": "Salary", "type": "income"},
            ],
        },
        "expected_output": {"category_name": "Salary", "allow_null": False},
        "metadata": {
            "dataset_name": CATEGORY_CLASSIFIER_DATASET_NAME,
            "case_tags": ["guardrail", "income_vs_expense"],
            "expected_type": "income",
        },
    },
    {
        "name": "category_classifier_transfer_guardrail",
        "input": {
            "rows": [
                {
                    "source_row_number": 1,
                    "description": "Transferencia a ahorro",
                    "notes": "Movimiento espejo",
                    "amount": "-350.00",
                    "currency": "EUR",
                }
            ],
            "categories": [
                {"name": "Transfer", "type": "transfer"},
                {"name": "Leisure", "type": "expense"},
            ],
        },
        "expected_output": {"category_name": "Transfer", "allow_null": False},
        "metadata": {
            "dataset_name": CATEGORY_CLASSIFIER_DATASET_NAME,
            "case_tags": ["guardrail", "transfer"],
            "expected_type": "transfer",
        },
    },
    {
        "name": "category_classifier_low_confidence_returns_null",
        "input": {
            "rows": [
                {
                    "source_row_number": 1,
                    "description": "Generic payment",
                    "notes": None,
                    "amount": "-10.00",
                    "currency": "EUR",
                }
            ],
            "categories": [
                {"name": "Groceries", "type": "expense"},
                {"name": "Transport", "type": "expense"},
            ],
        },
        "expected_output": {"category_name": None, "allow_null": True},
        "metadata": {
            "dataset_name": CATEGORY_CLASSIFIER_DATASET_NAME,
            "case_tags": ["ambiguous", "null_expected"],
            "expected_type": "expense",
        },
    },
    {
        "name": "category_classifier_multilingual_transport_match",
        "input": {
            "rows": [
                {
                    "source_row_number": 1,
                    "description": "TMB Metro Barcelona",
                    "notes": "Billete sencillo",
                    "amount": "-2.55",
                    "currency": "EUR",
                }
            ],
            "categories": [
                {"name": "Transport", "type": "expense"},
                {"name": "Leisure", "type": "expense"},
                {"name": "Groceries", "type": "expense"},
            ],
        },
        "expected_output": {"category_name": "Transport", "allow_null": False},
        "metadata": {
            "dataset_name": CATEGORY_CLASSIFIER_DATASET_NAME,
            "case_tags": ["multilingual", "merchant_match"],
            "expected_type": "expense",
        },
    },
    {
        "name": "category_classifier_notes_disambiguate_subscription",
        "input": {
            "rows": [
                {
                    "source_row_number": 1,
                    "description": "Apple.com Bill",
                    "notes": "iCloud monthly storage",
                    "amount": "-2.99",
                    "currency": "EUR",
                }
            ],
            "categories": [
                {"name": "Subscriptions", "type": "expense"},
                {"name": "Leisure", "type": "expense"},
                {"name": "Transfer", "type": "transfer"},
            ],
        },
        "expected_output": {"category_name": "Subscriptions", "allow_null": False},
        "metadata": {
            "dataset_name": CATEGORY_CLASSIFIER_DATASET_NAME,
            "case_tags": ["notes_signal", "recurring_payment"],
            "expected_type": "expense",
        },
    },
]

DATASET_DEFINITIONS = {
    PDF_PARSER_DATASET_NAME: {
        "description": "Baseline parser eval cases for OCR-to-transactions flow.",
        "items": PDF_PARSER_CASES,
    },
    CATEGORY_CLASSIFIER_DATASET_NAME: {
        "description": "Baseline classification eval cases for transaction category assistant.",
        "items": CATEGORY_CLASSIFIER_CASES,
    },
}
