from io import BytesIO

from openpyxl import Workbook


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
