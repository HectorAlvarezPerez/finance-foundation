from io import BytesIO

from openpyxl import Workbook

from app.services import transaction_import_service as transaction_import_module
from app.services.azure_document_intelligence_ocr_service import (
    OcrExtractionResult,
    OcrTable,
    OcrTableCell,
)


def build_text_pdf(lines: list[str]) -> bytes:
    content_lines = ["BT", "/F1 12 Tf", "72 720 Td"]
    for index, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index > 0:
            content_lines.append("T*")
        content_lines.append(f"({escaped}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("utf-8")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def test_create_and_list_transactions(client, user_id) -> None:
    account_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Main Account",
            "type": "checking",
            "currency": "EUR",
        },
    )
    assert account_response.status_code == 201
    account_id = account_response.json()["id"]

    category_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Groceries",
            "type": "expense",
            "color": "#22c55e",
            "icon": "shopping-cart",
        },
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    transaction_response = client.post(
        "/api/v1/transactions",
        headers={"X-User-Id": str(user_id)},
        json={
            "account_id": account_id,
            "category_id": category_id,
            "date": "2026-03-01",
            "amount": "48.90",
            "currency": "EUR",
            "description": "Weekly groceries",
            "notes": "Local market",
        },
    )

    assert transaction_response.status_code == 201
    created = transaction_response.json()
    assert created["description"] == "Weekly groceries"
    assert created["amount"] == "48.90"

    list_response = client.get(
        "/api/v1/transactions?category_id=" + category_id,
        headers={"X-User-Id": str(user_id)},
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["description"] == "Weekly groceries"


def test_rejects_transaction_when_currency_does_not_match_account(client, user_id) -> None:
    account_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Savings",
            "type": "savings",
            "currency": "EUR",
        },
    )
    assert account_response.status_code == 201
    account_id = account_response.json()["id"]

    transaction_response = client.post(
        "/api/v1/transactions",
        headers={"X-User-Id": str(user_id)},
        json={
            "account_id": account_id,
            "category_id": None,
            "date": "2026-03-05",
            "amount": "100.00",
            "currency": "USD",
            "description": "Invalid currency test",
            "notes": None,
        },
    )

    assert transaction_response.status_code == 400
    assert (
        transaction_response.json()["detail"]
        == "Transaction currency must match the selected account currency"
    )


def test_filters_transactions_by_search_and_date_range(client, user_id) -> None:
    account_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Daily Use",
            "type": "checking",
            "currency": "EUR",
        },
    )
    assert account_response.status_code == 201
    account_id = account_response.json()["id"]

    first = client.post(
        "/api/v1/transactions",
        headers={"X-User-Id": str(user_id)},
        json={
            "account_id": account_id,
            "category_id": None,
            "date": "2026-03-10",
            "amount": "12.50",
            "currency": "EUR",
            "description": "Coffee beans",
            "notes": "special roast",
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/transactions",
        headers={"X-User-Id": str(user_id)},
        json={
            "account_id": account_id,
            "category_id": None,
            "date": "2026-03-20",
            "amount": "60.00",
            "currency": "EUR",
            "description": "Electric bill",
            "notes": "home services",
        },
    )
    assert second.status_code == 201

    filtered = client.get(
        "/api/v1/transactions?search=coffee&date_from=2026-03-01&date_to=2026-03-15",
        headers={"X-User-Id": str(user_id)},
    )

    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["total"] == 1
    assert payload["items"][0]["description"] == "Coffee beans"


def test_filters_transactions_by_category_type(client, user_id) -> None:
    account_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Daily Use",
            "type": "checking",
            "currency": "EUR",
        },
    )
    assert account_response.status_code == 201
    account_id = account_response.json()["id"]

    expense_category_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Groceries",
            "type": "expense",
            "color": "#22c55e",
            "icon": "shopping-cart",
        },
    )
    assert expense_category_response.status_code == 201
    expense_category_id = expense_category_response.json()["id"]

    income_category_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Salary",
            "type": "income",
            "color": "#16a34a",
            "icon": "wallet",
        },
    )
    assert income_category_response.status_code == 201
    income_category_id = income_category_response.json()["id"]

    expense_transaction = client.post(
        "/api/v1/transactions",
        headers={"X-User-Id": str(user_id)},
        json={
            "account_id": account_id,
            "category_id": expense_category_id,
            "date": "2026-03-10",
            "amount": "-24.50",
            "currency": "EUR",
            "description": "Groceries",
            "notes": "Weekly shop",
        },
    )
    assert expense_transaction.status_code == 201

    income_transaction = client.post(
        "/api/v1/transactions",
        headers={"X-User-Id": str(user_id)},
        json={
            "account_id": account_id,
            "category_id": income_category_id,
            "date": "2026-03-15",
            "amount": "2500.00",
            "currency": "EUR",
            "description": "Salary",
            "notes": "Monthly income",
        },
    )
    assert income_transaction.status_code == 201

    expense_filtered = client.get(
        "/api/v1/transactions?category_type=expense",
        headers={"X-User-Id": str(user_id)},
    )

    assert expense_filtered.status_code == 200
    expense_payload = expense_filtered.json()
    assert expense_payload["total"] == 1
    assert expense_payload["items"][0]["description"] == "Groceries"

    income_filtered = client.get(
        "/api/v1/transactions?category_type=income",
        headers={"X-User-Id": str(user_id)},
    )

    assert income_filtered.status_code == 200
    income_payload = income_filtered.json()
    assert income_payload["total"] == 1
    assert income_payload["items"][0]["description"] == "Salary"


def test_analyze_and_commit_transaction_import_from_csv(client, user_id) -> None:
    account_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Import Account",
            "type": "checking",
            "currency": "EUR",
        },
    )
    assert account_response.status_code == 201
    account_id = account_response.json()["id"]

    category_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Groceries",
            "type": "expense",
            "color": "#22c55e",
            "icon": "shopping-cart",
        },
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    csv_content = (
        "Fecha,Importe,Merchant,Categoria,Notas\n"
        "01/03/2026,48.90,Weekly groceries,Groceries,Imported from CSV\n"
        "02/03/2026,12.40,Coffee,,Morning stop\n"
    )

    analyze_response = client.post(
        "/api/v1/transactions/import/analyze",
        files={"file": ("transactions.csv", csv_content, "text/csv")},
        headers={"X-User-Id": str(user_id)},
    )

    assert analyze_response.status_code == 200
    analyze_payload = analyze_response.json()
    assert analyze_payload["source_type"] == "csv"
    assert analyze_payload["total_rows"] == 2
    assert analyze_payload["suggested_mapping"]["date"] == "Fecha"
    assert analyze_payload["suggested_mapping"]["amount"] == "Importe"
    assert analyze_payload["suggested_mapping"]["description"] == "Merchant"

    preview_response = client.post(
        "/api/v1/transactions/import/preview",
        headers={"X-User-Id": str(user_id)},
        files={"file": ("transactions.csv", csv_content, "text/csv")},
        data={
            "account_id": account_id,
            "mapping": (
                '{"date":"Fecha","amount":"Importe","description":"Merchant",'
                '"category":"Categoria","notes":"Notas"}'
            ),
        },
    )

    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["account_id"] == account_id
    assert preview_payload["rows"][0]["category_id"] == category_id
    assert preview_payload["rows"][0]["description"] == "Weekly groceries"
    assert preview_payload["rows"][0]["validation_errors"] == []

    commit_response = client.post(
        "/api/v1/transactions/import/commit",
        headers={"X-User-Id": str(user_id)},
        json={
            "items": [
                {
                    "account_id": account_id,
                    "category_id": category_id,
                    "date": "2026-03-01",
                    "amount": "48.90",
                    "currency": "EUR",
                    "description": "Weekly groceries",
                    "notes": "Imported from CSV",
                    "source_row_number": 1,
                },
                {
                    "account_id": account_id,
                    "category_id": None,
                    "date": "2026-03-02",
                    "amount": "12.40",
                    "currency": "EUR",
                    "description": "Coffee",
                    "notes": "Morning stop",
                    "source_row_number": 2,
                },
            ]
        },
    )

    assert commit_response.status_code == 200
    assert commit_response.json()["imported_count"] == 2

    list_response = client.get(
        "/api/v1/transactions",
        headers={"X-User-Id": str(user_id)},
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 2


def test_does_not_map_type_column_as_category_suggestion(client, user_id) -> None:
    csv_content = (
        "Tipo,Importe,Merchant,Fecha\nPago con tarjeta,48.90,Weekly groceries,01/03/2026\n"
    )

    analyze_response = client.post(
        "/api/v1/transactions/import/analyze",
        files={"file": ("transactions.csv", csv_content, "text/csv")},
        headers={"X-User-Id": str(user_id)},
    )

    assert analyze_response.status_code == 200
    analyze_payload = analyze_response.json()
    assert analyze_payload["suggested_mapping"]["category"] is None


def test_maps_start_date_and_description_columns_from_bank_like_import(client, user_id) -> None:
    csv_content = (
        "Tipo,Producto,Fecha de inicio,Fecha de finalización,"
        "Descripción,Importe,Comisión,Divisa,State,Saldo\n"
        "Pago con tarjeta,Actual,01/04/2026 13:07:49,02/04/2026 11:45:19,"
        "Botiga Olot,-12.40,0,EUR,booked,1200.00\n"
    )

    analyze_response = client.post(
        "/api/v1/transactions/import/analyze",
        files={"file": ("transactions.csv", csv_content, "text/csv")},
        headers={"X-User-Id": str(user_id)},
    )

    assert analyze_response.status_code == 200
    analyze_payload = analyze_response.json()
    assert analyze_payload["suggested_mapping"]["date"] == "Fecha de inicio"
    assert analyze_payload["suggested_mapping"]["amount"] == "Importe"
    assert analyze_payload["suggested_mapping"]["description"] == "Descripción"
    assert analyze_payload["suggested_mapping"]["category"] is None


def test_preview_parses_bank_like_datetime_date_column(client, user_id) -> None:
    account_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Import Account",
            "type": "checking",
            "currency": "EUR",
        },
    )
    assert account_response.status_code == 201
    account_id = account_response.json()["id"]

    csv_content = (
        "Tipo,Producto,Fecha de inicio,Fecha de finalización,"
        "Descripción,Importe,Comisión,Divisa,State,Saldo\n"
        "Pago con tarjeta,Actual,01/04/2026 13:07:49,02/04/2026 11:45:19,"
        "Botiga Olot,-12.40,0,EUR,booked,1200.00\n"
    )

    preview_response = client.post(
        "/api/v1/transactions/import/preview",
        headers={"X-User-Id": str(user_id)},
        files={"file": ("transactions.csv", csv_content, "text/csv")},
        data={
            "account_id": account_id,
            "mapping": (
                '{"date":"Fecha de inicio","amount":"Importe",'
                '"description":"Descripción","category":"","notes":""}'
            ),
        },
    )

    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["rows"][0]["date"] == "2026-04-01"
    assert preview_payload["rows"][0]["description"] == "Botiga Olot"
    assert preview_payload["rows"][0]["amount"] == "-12.40"
    assert "Review the date" not in preview_payload["rows"][0]["validation_errors"]


def test_preview_transaction_import_from_excel(client, user_id) -> None:
    account_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Excel Account",
            "type": "checking",
            "currency": "EUR",
        },
    )
    assert account_response.status_code == 201
    account_id = account_response.json()["id"]

    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["Date", "Amount", "Description", "Notes"])
    sheet.append(["2026-03-07", "14.75", "Lunch", "Imported from Excel"])
    buffer = BytesIO()
    workbook.save(buffer)
    excel_content = buffer.getvalue()

    preview_response = client.post(
        "/api/v1/transactions/import/preview",
        headers={"X-User-Id": str(user_id)},
        files={
            "file": (
                "transactions.xlsx",
                excel_content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={
            "account_id": account_id,
            "mapping": (
                '{"date":"Date","amount":"Amount","description":"Description","notes":"Notes"}'
            ),
        },
    )

    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["source_type"] == "excel"
    assert preview_payload["rows"][0]["description"] == "Lunch"
    assert preview_payload["rows"][0]["validation_errors"] == []


def test_preview_transaction_import_from_pdf(client, user_id, monkeypatch) -> None:
    class FakeAzureDocumentIntelligenceOcrService:
        def extract_text(self, *, content: bytes) -> OcrExtractionResult:
            transaction_table = OcrTable(
                row_count=5,
                column_count=7,
                page_number=1,
                top=7.48,
                bbox=(0.54, 7.48, 7.73, 8.82),
                cells=[
                    OcrTableCell(0, 0, "Fecha de la transacción", "COLUMN_HEADER"),
                    OcrTableCell(0, 1, "Fecha valor", "COLUMN_HEADER"),
                    OcrTableCell(0, 2, "Descripción", "COLUMN_HEADER"),
                    OcrTableCell(0, 3, "Dinero saliente", "COLUMN_HEADER"),
                    OcrTableCell(0, 5, "Dinero entrante", "COLUMN_HEADER"),
                    OcrTableCell(0, 6, "Saldo", "COLUMN_HEADER"),
                    OcrTableCell(1, 0, "1 abr 2026"),
                    OcrTableCell(1, 1, "1 abr 2026"),
                    OcrTableCell(1, 2, "Servei d Activitat Fisica (SAF)"),
                    OcrTableCell(1, 3, "13,00€"),
                    OcrTableCell(1, 6, "692,91"),
                    OcrTableCell(
                        2,
                        2,
                        "Referencia: QUOTA D'ABONAMENT MES D'ABRIL 2026",
                    ),
                    OcrTableCell(2, 6, "€"),
                    OcrTableCell(3, 0, "1 abr 2026"),
                    OcrTableCell(3, 1, "2 abr 2026"),
                    OcrTableCell(3, 2, "Botiga Olot"),
                    OcrTableCell(3, 3, "4,98€"),
                    OcrTableCell(3, 6, "687,93"),
                ],
            )
            return OcrExtractionResult(
                text="\n".join(
                    [
                        "01/04/2026 Grocery Store -12.40",
                        "02/04/2026 Coffee Shop -3.50",
                    ]
                ),
                page_count=1,
                tables_markdown=(
                    "## Table 4\n"
                    "| Fecha de la transacción | Fecha valor | Descripción | Dinero saliente | "
                    "| | Dinero entrante | Saldo |\n"
                    "| --- | --- | --- | --- | --- | --- | --- |\n"
                    "| 1 abr 2026 | 1 abr 2026 | Servei d Activitat Fisica (SAF) | "
                    "13,00€ | | | 692,91 |\n"
                    "| | | Referencia: QUOTA D'ABONAMENT MES D'ABRIL 2026 | | | | € |\n"
                    "| 1 abr 2026 | 2 abr 2026 | Botiga Olot | 4,98€ | | | 687,93 |\n"
                ),
                structured_text=(
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
                tables=[transaction_table],
            )

    class FakeAzureOpenAIPdfParserService:
        @property
        def enabled(self) -> bool:
            return False

        def parse_transactions(
            self,
            *,
            structured_text: str,
            tables_markdown: str,
        ) -> list[dict[str, str]]:
            return []

    monkeypatch.setattr(
        transaction_import_module,
        "AzureDocumentIntelligenceOcrService",
        FakeAzureDocumentIntelligenceOcrService,
    )
    monkeypatch.setattr(
        transaction_import_module,
        "AzureOpenAIPdfParserService",
        FakeAzureOpenAIPdfParserService,
    )

    account_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "PDF Account",
            "type": "checking",
            "currency": "EUR",
        },
    )
    assert account_response.status_code == 201
    account_id = account_response.json()["id"]

    pdf_content = build_text_pdf(["Mocked OCR payload"])

    analyze_response = client.post(
        "/api/v1/transactions/import/analyze",
        files={"file": ("transactions.pdf", pdf_content, "application/pdf")},
        headers={"X-User-Id": str(user_id)},
    )

    assert analyze_response.status_code == 200
    analyze_payload = analyze_response.json()
    assert analyze_payload["source_type"] == "pdf"
    assert analyze_payload["suggested_mapping"]["date"] == "Fecha"
    assert analyze_payload["suggested_mapping"]["amount"] == "Importe"
    assert analyze_payload["suggested_mapping"]["description"] == "Descripción"
    assert analyze_payload["total_rows"] == 2
    assert "texto estructurado" in analyze_payload["message"]

    preview_response = client.post(
        "/api/v1/transactions/import/preview",
        headers={"X-User-Id": str(user_id)},
        files={"file": ("transactions.pdf", pdf_content, "application/pdf")},
        data={
            "account_id": account_id,
            "mapping": '{"date":"","amount":"","description":"","category":"","notes":""}',
        },
    )

    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["source_type"] == "pdf"
    assert preview_payload["rows"][0]["date"] == "2026-04-01"
    assert preview_payload["rows"][0]["description"] == "Servei d Activitat Fisica (SAF)"
    assert preview_payload["rows"][0]["amount"] == "-13.00"
    assert preview_payload["rows"][0]["validation_errors"] == []


def test_pdf_import_uses_llm_fallback_when_table_parser_finds_no_rows(
    client,
    user_id,
    monkeypatch,
) -> None:
    class FakeAzureDocumentIntelligenceOcrService:
        def extract_text(self, *, content: bytes) -> OcrExtractionResult:
            return OcrExtractionResult(
                text="Random OCR text",
                page_count=1,
                tables_markdown="## Table 1\n| col | col2 |",
                structured_text="# Page 1\nSome OCR",
                tables=[],
            )

    class FakeAzureOpenAIPdfParserService:
        @property
        def enabled(self) -> bool:
            return True

        def parse_transactions(
            self,
            *,
            structured_text: str,
            tables_markdown: str,
        ) -> list[dict[str, str]]:
            return [
                {
                    "Fecha": "2026-04-02",
                    "Descripción": "Ametller Origen",
                    "Importe": "-2.09",
                }
            ]

    monkeypatch.setattr(
        transaction_import_module,
        "AzureDocumentIntelligenceOcrService",
        FakeAzureDocumentIntelligenceOcrService,
    )
    monkeypatch.setattr(
        transaction_import_module,
        "AzureOpenAIPdfParserService",
        FakeAzureOpenAIPdfParserService,
    )

    analyze_response = client.post(
        "/api/v1/transactions/import/analyze",
        files={
            "file": (
                "transactions.pdf",
                build_text_pdf(["Mocked OCR payload"]),
                "application/pdf",
            )
        },
        headers={"X-User-Id": str(user_id)},
    )

    assert analyze_response.status_code == 200
    analyze_payload = analyze_response.json()
    assert analyze_payload["total_rows"] == 1
    assert "capa asistida" in analyze_payload["message"]
