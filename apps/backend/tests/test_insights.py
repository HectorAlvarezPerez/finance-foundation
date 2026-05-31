def test_get_insights_summary(client, user_id) -> None:
    checking_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Cuenta principal",
            "bank_name": "Santander",
            "type": "checking",
            "currency": "EUR",
        },
    )
    assert checking_response.status_code == 201
    checking_id = checking_response.json()["id"]

    savings_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Ahorro",
            "bank_name": "ING",
            "type": "savings",
            "currency": "EUR",
        },
    )
    assert savings_response.status_code == 201
    savings_id = savings_response.json()["id"]

    food_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Comida",
            "type": "expense",
            "color": "#f97316",
            "icon": "utensils",
        },
    )
    assert food_response.status_code == 201
    food_id = food_response.json()["id"]

    salary_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Salario",
            "type": "income",
            "color": "#16a34a",
            "icon": "briefcase",
        },
    )
    assert salary_response.status_code == 201
    salary_id = salary_response.json()["id"]

    transfer_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Traspasos",
            "type": "transfer",
            "color": "#6366f1",
            "icon": "arrow-left-right",
        },
    )
    assert transfer_response.status_code == 201
    transfer_id = transfer_response.json()["id"]

    transactions = [
        {
            "account_id": checking_id,
            "category_id": salary_id,
            "date": "2026-03-01",
            "amount": "2000.00",
            "currency": "EUR",
            "description": "Nómina marzo",
        },
        {
            "account_id": checking_id,
            "category_id": food_id,
            "date": "2026-03-03",
            "amount": "-45.00",
            "currency": "EUR",
            "description": "Supermercado",
        },
        {
            "account_id": savings_id,
            "category_id": None,
            "date": "2026-02-15",
            "amount": "100.00",
            "currency": "EUR",
            "description": "Traspaso ahorro",
        },
        {
            "account_id": checking_id,
            "category_id": transfer_id,
            "date": "2026-03-10",
            "amount": "-200.00",
            "currency": "EUR",
            "description": "Traspaso a ahorro (salida)",
        },
        {
            "account_id": savings_id,
            "category_id": transfer_id,
            "date": "2026-03-10",
            "amount": "200.00",
            "currency": "EUR",
            "description": "Traspaso a ahorro (entrada)",
        },
    ]

    for payload in transactions:
        response = client.post(
            "/api/v1/transactions",
            headers={"X-User-Id": str(user_id)},
            json=payload,
        )
        assert response.status_code == 201

    summary_response = client.get(
        "/api/v1/insights/summary",
        headers={"X-User-Id": str(user_id)},
    )

    assert summary_response.status_code == 200
    payload = summary_response.json()
    # Transfers (categoría tipo "transfer") mueven dinero entre cuentas propias:
    # afectan al saldo pero NO deben contar como ingreso ni como gasto.
    assert payload["income"] == "2100.00"
    assert payload["expenses"] == "45.00"
    assert payload["balance"] == "2055.00"
    assert payload["transaction_count"] == 5

    assert payload["top_categories"][0]["name"] == "Comida"
    assert payload["top_categories"][0]["total"] == "45.00"
    category_names = {item["name"] for item in payload["top_categories"]}
    assert "Traspasos" not in category_names

    assert payload["monthly_comparison"][0]["month_key"] == "2026-02"
    assert payload["monthly_comparison"][0]["income"] == "100.00"
    assert payload["monthly_comparison"][1]["month_key"] == "2026-03"
    assert payload["monthly_comparison"][1]["income"] == "2000.00"
    assert payload["monthly_comparison"][1]["expenses"] == "45.00"

    account_names = [item["name"] for item in payload["account_balances"]]
    assert account_names == ["Cuenta principal", "Ahorro"]


def test_net_worth_endpoint(client, user_id) -> None:
    headers = {"X-User-Id": str(user_id)}
    account_id = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"name": "Principal", "bank_name": "X", "type": "checking", "currency": "EUR"},
    ).json()["id"]

    for payload in (
        {"date": "2026-01-10", "amount": "1000.00", "description": "Nómina enero"},
        {"date": "2026-02-05", "amount": "-200.00", "description": "Compra"},
    ):
        response = client.post(
            "/api/v1/transactions",
            headers=headers,
            json={"account_id": account_id, "category_id": None, "currency": "EUR", **payload},
        )
        assert response.status_code == 201

    net_worth = client.get("/api/v1/insights/net-worth", headers=headers)
    assert net_worth.status_code == 200
    data = net_worth.json()
    assert data["accounts_value"] == "800.00"
    assert data["investments_value"] == "0"
    assert data["net_worth"] == "800.00"
    assert [point["month_key"] for point in data["history"]] == ["2026-01", "2026-02"]
    assert data["history"][0]["value"] == "1000.00"
    assert data["history"][1]["value"] == "800.00"
