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
    # Income/expense classification uses category type, not amount sign.
    # Uncategorized transactions (like "Traspaso ahorro") affect balance but are
    # not counted as income or expense until categorized.
    # Transfers (categoría tipo "transfer") are excluded from cash-flow totals.
    assert payload["income"] == "2000.00"
    assert payload["expenses"] == "45.00"
    assert payload["balance"] == "2055.00"
    assert payload["transaction_count"] == 5
    # savings_rate = (income - expenses) / income * 100
    assert payload["savings_rate"] == 97.75

    assert payload["top_categories"][0]["name"] == "Comida"
    assert payload["top_categories"][0]["total"] == "45.00"
    category_names = {item["name"] for item in payload["top_categories"]}
    assert "Traspasos" not in category_names

    assert payload["monthly_comparison"][0]["month_key"] == "2026-02"
    assert payload["monthly_comparison"][0]["income"] == "0.00"
    assert payload["monthly_comparison"][1]["month_key"] == "2026-03"
    assert payload["monthly_comparison"][1]["income"] == "2000.00"
    assert payload["monthly_comparison"][1]["expenses"] == "45.00"

    account_names = [item["name"] for item in payload["account_balances"]]
    assert account_names == ["Cuenta principal", "Ahorro"]


def _setup_two_month_dataset(client, user_id) -> dict[str, str]:
    """Two past months of activity (2025-04 and 2025-05) across two accounts."""
    headers = {"X-User-Id": str(user_id)}

    checking_id = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"name": "Cuenta", "bank_name": "X", "type": "checking", "currency": "EUR"},
    ).json()["id"]
    savings_id = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"name": "Ahorro", "bank_name": "Y", "type": "savings", "currency": "EUR"},
    ).json()["id"]

    food_id = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "Comida", "type": "expense", "color": "#f97316", "icon": "utensils"},
    ).json()["id"]
    salary_id = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "Salario", "type": "income", "color": "#16a34a", "icon": "briefcase"},
    ).json()["id"]
    transfer_id = client.post(
        "/api/v1/categories",
        headers=headers,
        json={
            "name": "Traspasos",
            "type": "transfer",
            "color": "#6366f1",
            "icon": "arrow-left-right",
        },
    ).json()["id"]

    transactions = [
        # (account_id, category_id, date, amount, description)
        # 2025-04 (previous month for pacing)
        (checking_id, salary_id, "2025-04-02", "1500.00", "Nómina abril"),
        (checking_id, food_id, "2025-04-08", "-30.00", "Supermercado"),
        (checking_id, food_id, "2025-04-20", "-100.00", "Restaurante"),
        # 2025-05 (selected month)
        (checking_id, salary_id, "2025-05-01", "2000.00", "Nómina mayo"),
        (checking_id, food_id, "2025-05-10", "-45.00", "Supermercado"),
        (savings_id, transfer_id, "2025-05-15", "200.00", "Traspaso"),
        (checking_id, None, "2025-05-20", "50.00", "Sin categoría"),
    ]
    for account_id, category_id, tx_date, amount, description in transactions:
        response = client.post(
            "/api/v1/transactions",
            headers=headers,
            json={
                "account_id": account_id,
                "category_id": category_id,
                "date": tx_date,
                "amount": amount,
                "currency": "EUR",
                "description": description,
            },
        )
        assert response.status_code == 201

    return headers


def test_insights_summary_month_scoped(client, user_id) -> None:
    headers = _setup_two_month_dataset(client, user_id)

    unscoped = client.get("/api/v1/insights/summary", headers=headers)
    assert unscoped.status_code == 200
    unscoped_payload = unscoped.json()

    scoped = client.get(
        "/api/v1/insights/summary",
        headers=headers,
        params={"month_key": "2025-05"},
    )
    assert scoped.status_code == 200
    payload = scoped.json()

    # Cash-flow figures restricted to 2025-05 (transfers count as movements).
    assert payload["income"] == "2000.00"
    assert payload["expenses"] == "45.00"
    assert payload["transaction_count"] == 4
    assert payload["savings_rate"] == 97.75

    assert [(item["name"], item["total"]) for item in payload["expense_categories"]] == [
        ("Comida", "45.00")
    ]
    assert [(item["name"], item["total"]) for item in payload["top_categories"]] == [
        ("Comida", "45.00")
    ]

    # Global fields are identical to the unscoped response.
    assert payload["balance"] == unscoped_payload["balance"]
    assert payload["account_balances"] == unscoped_payload["account_balances"]
    assert payload["monthly_comparison"] == unscoped_payload["monthly_comparison"]
    assert payload["available_recap_months"] == unscoped_payload["available_recap_months"]

    # Unscoped cash flow keeps covering everything.
    assert unscoped_payload["income"] == "3500.00"
    assert unscoped_payload["expenses"] == "175.00"
    assert unscoped_payload["transaction_count"] == 7


def test_insights_summary_month_scoped_daily_pacing(client, user_id) -> None:
    headers = _setup_two_month_dataset(client, user_id)

    payload = client.get(
        "/api/v1/insights/summary",
        headers=headers,
        params={"month_key": "2025-05"},
    ).json()

    pacing = {item["day"]: item for item in payload["daily_pacing"]}
    assert len(pacing) == 31

    # Selected month (2025-05) cumulative expenses; past months are not truncated.
    assert pacing[9]["current_month_cumulative"] == "0.00"
    assert pacing[10]["current_month_cumulative"] == "45.00"
    assert pacing[31]["current_month_cumulative"] == "45.00"

    # Previous-month series is the immediately preceding calendar month (2025-04).
    assert pacing[7]["previous_month_cumulative"] == "0.00"
    assert pacing[8]["previous_month_cumulative"] == "30.00"
    assert pacing[20]["previous_month_cumulative"] == "130.00"
    assert pacing[31]["previous_month_cumulative"] == "130.00"


def test_insights_summary_month_scoped_empty_month(client, user_id) -> None:
    headers = _setup_two_month_dataset(client, user_id)

    response = client.get(
        "/api/v1/insights/summary",
        headers=headers,
        params={"month_key": "2024-01"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["income"] == "0.00"
    assert payload["expenses"] == "0.00"
    assert payload["transaction_count"] == 0
    assert payload["savings_rate"] == 0.0
    assert payload["expense_categories"] == []
    assert payload["top_categories"] == []
    # Empty past month still yields the full, zeroed pacing series.
    assert all(
        item["current_month_cumulative"] == "0.00"
        and item["previous_month_cumulative"] == "0.00"
        for item in payload["daily_pacing"]
    )
    # Global figures remain intact.
    assert payload["balance"] == "3575.00"


def test_insights_summary_invalid_month_key(client, user_id) -> None:
    headers = {"X-User-Id": str(user_id)}
    for invalid in ("2025-5", "202505", "total", "2025-05-01"):
        response = client.get(
            "/api/v1/insights/summary",
            headers=headers,
            params={"month_key": invalid},
        )
        assert response.status_code == 422


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


def test_subscriptions_detection(client, user_id) -> None:
    headers = {"X-User-Id": str(user_id)}
    account_id = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"name": "Cuenta", "bank_name": "X", "type": "checking", "currency": "EUR"},
    ).json()["id"]

    for month in (1, 2, 3):
        response = client.post(
            "/api/v1/transactions",
            headers=headers,
            json={
                "account_id": account_id,
                "category_id": None,
                "date": f"2026-0{month}-15",
                "amount": "-12.99",
                "currency": "EUR",
                "description": "Netflix Espana 0001",
            },
        )
        assert response.status_code == 201

    # one-off purchase, must NOT be detected as a subscription
    client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": account_id,
            "category_id": None,
            "date": "2026-02-20",
            "amount": "-80.00",
            "currency": "EUR",
            "description": "Compra puntual zapatos",
        },
    )

    subscriptions = client.get("/api/v1/insights/subscriptions", headers=headers)
    assert subscriptions.status_code == 200
    data = subscriptions.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert "Netflix" in item["label"]
    assert item["occurrences"] == 3
    assert item["monthly_estimate"] == "12.99"
    assert data["total_monthly_estimate"] == "12.99"
