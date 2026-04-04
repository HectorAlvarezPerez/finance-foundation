from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.azure_openai_pdf_parser_service import AzureOpenAIPdfParserService
from app.services.transaction_import_service import TransactionImportService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare the deterministic PDF parser with the Azure OpenAI fallback "
            "using OCR artifacts generated from a bank statement PDF."
        )
    )
    parser.add_argument(
        "structured_text",
        type=Path,
        help="Path to the OCR structured text file (*.ocr.structured.txt)",
    )
    parser.add_argument(
        "--tables",
        type=Path,
        default=None,
        help="Optional path to the OCR tables markdown file (*.ocr.tables.md)",
    )
    return parser.parse_args()


def infer_tables_path(structured_text_path: Path) -> Path:
    return structured_text_path.with_name(
        structured_text_path.name.replace(".ocr.structured.txt", ".ocr.tables.md")
    )


def main() -> None:
    args = parse_args()
    structured_text_path = args.structured_text
    tables_path = args.tables or infer_tables_path(structured_text_path)

    structured_text = structured_text_path.read_text(encoding="utf-8")
    tables_markdown = tables_path.read_text(encoding="utf-8") if tables_path.exists() else ""

    import_service = TransactionImportService(
        repository=None,  # type: ignore[arg-type]
        account_repository=None,  # type: ignore[arg-type]
        category_repository=None,  # type: ignore[arg-type]
        db=None,  # type: ignore[arg-type]
    )
    llm_service = AzureOpenAIPdfParserService()

    deterministic_rows = import_service._extract_rows_from_pdf_structured_text(structured_text)
    llm_rows = llm_service.parse_transactions(
        structured_text=structured_text,
        tables_markdown=tables_markdown,
    )

    print("=== OCR artifacts ===")
    print(
        json.dumps(
            {
                "structured_text_path": str(structured_text_path),
                "tables_path": str(tables_path) if tables_markdown else None,
                "llm_enabled": llm_service.enabled,
                "llm_deployment": llm_service.deployment,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print()

    print("=== Deterministic parser ===")
    print(json.dumps(deterministic_rows, indent=2, ensure_ascii=False))
    print()

    print("=== LLM fallback ===")
    print(json.dumps(llm_rows, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
