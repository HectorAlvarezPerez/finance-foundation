def test_create_and_list_budgets(client, user_id) -> None:
    category_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Housing",
            "type": "expense",
            "color": "#0f766e",
            "icon": "house",
        },
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    budget_response = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "year": 2026,
            "month": 3,
            "currency": "EUR",
            "amount": "1200.00",
        },
    )

    assert budget_response.status_code == 201
    created = budget_response.json()
    assert created["amount"] == "1200.00"
    assert created["month"] == 3

    list_response = client.get(
        "/api/v1/budgets?year=2026&month=3",
        headers={"X-User-Id": str(user_id)},
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["category_id"] == category_id


def test_prevents_duplicate_budget_for_same_category_and_month(client, user_id) -> None:
    category_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Food",
            "type": "expense",
            "color": "#f97316",
            "icon": "utensils",
        },
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    first = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "year": 2026,
            "month": 4,
            "currency": "EUR",
            "amount": "350.00",
        },
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "year": 2026,
            "month": 4,
            "currency": "EUR",
            "amount": "400.00",
        },
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "A budget already exists for this category and month"


def test_create_and_list_annual_budget(client, user_id) -> None:
    category_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Travel",
            "type": "expense",
            "color": "#7c3aed",
            "icon": "plane",
        },
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    budget_response = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "year": 2026,
            "period_type": "annual",
            "month": None,
            "currency": "EUR",
            "amount": "1800.00",
        },
    )

    assert budget_response.status_code == 201
    created = budget_response.json()
    assert created["period_type"] == "annual"
    assert created["month"] is None

    list_response = client.get(
        "/api/v1/budgets?year=2026&period_type=annual",
        headers={"X-User-Id": str(user_id)},
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == created["id"]


def test_prevents_duplicate_annual_budget_for_same_category_and_year(client, user_id) -> None:
    category_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Trips",
            "type": "expense",
            "color": "#06b6d4",
            "icon": "plane",
        },
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    first = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "year": 2026,
            "period_type": "annual",
            "month": None,
            "currency": "EUR",
            "amount": "1000.00",
        },
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "year": 2026,
            "period_type": "annual",
            "month": None,
            "currency": "EUR",
            "amount": "1200.00",
        },
    )

    assert duplicate.status_code == 409
    assert (
        duplicate.json()["detail"]
        == "An annual budget already exists for this category and year"
    )


def test_create_budgets_for_multiple_months(client, user_id) -> None:
    category_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Cafe",
            "type": "expense",
            "color": "#2563eb",
            "icon": "coffee",
        },
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    bulk_response = client.post(
        "/api/v1/budgets/bulk",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "year": 2026,
            "months": [1, 2, 3],
            "currency": "EUR",
            "amount": "20.00",
        },
    )

    assert bulk_response.status_code == 201
    payload = bulk_response.json()
    assert payload["created_count"] == 3
    assert [item["month"] for item in payload["items"]] == [1, 2, 3]

    list_response = client.get(
        "/api/v1/budgets?year=2026",
        headers={"X-User-Id": str(user_id)},
    )

    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["total"] == 3


def test_prevents_duplicate_months_in_bulk_creation(client, user_id) -> None:
    category_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Selfcare",
            "type": "expense",
            "color": "#10b981",
            "icon": "heart",
        },
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    first = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "year": 2026,
            "month": 3,
            "currency": "EUR",
            "amount": "50.00",
        },
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/budgets/bulk",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "year": 2026,
            "months": [3, 4, 5],
            "currency": "EUR",
            "amount": "50.00",
        },
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Ya existe un presupuesto para los meses: 3"
