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
    assert payload["income"] == "2100.00"
    assert payload["expenses"] == "45.00"
    assert payload["balance"] == "2055.00"
    assert payload["transaction_count"] == 3

    assert payload["top_categories"][0]["name"] == "Comida"
    assert payload["top_categories"][0]["total"] == "45.00"

    assert payload["monthly_comparison"][0]["month_key"] == "2026-02"
    assert payload["monthly_comparison"][0]["income"] == "100.00"
    assert payload["monthly_comparison"][1]["month_key"] == "2026-03"
    assert payload["monthly_comparison"][1]["expenses"] == "45.00"

    account_names = [item["name"] for item in payload["account_balances"]]
    assert account_names == ["Cuenta principal", "Ahorro"]
