def _create_category(client, user_id, name: str) -> str:
    response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={"name": name, "type": "expense", "color": "#0f766e", "icon": "house"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_and_list_monthly_budget(client, user_id) -> None:
    category_id = _create_category(client, user_id, "Housing")

    budget_response = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "period_type": "monthly",
            "currency": "EUR",
            "amount": "1200.00",
        },
    )

    assert budget_response.status_code == 201
    created = budget_response.json()
    assert created["amount"] == "1200.00"
    assert created["period_type"] == "monthly"
    assert "year" not in created
    assert "month" not in created

    list_response = client.get(
        "/api/v1/budgets?period_type=monthly",
        headers={"X-User-Id": str(user_id)},
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["category_id"] == category_id


def test_prevents_duplicate_monthly_budget_for_same_category(client, user_id) -> None:
    category_id = _create_category(client, user_id, "Food")

    first = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "period_type": "monthly",
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
            "period_type": "monthly",
            "currency": "EUR",
            "amount": "400.00",
        },
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Ya existe un presupuesto mensual para esta categoría"


def test_create_and_list_annual_budget(client, user_id) -> None:
    category_id = _create_category(client, user_id, "Travel")

    budget_response = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "period_type": "annual",
            "currency": "EUR",
            "amount": "1800.00",
        },
    )

    assert budget_response.status_code == 201
    created = budget_response.json()
    assert created["period_type"] == "annual"

    list_response = client.get(
        "/api/v1/budgets?period_type=annual",
        headers={"X-User-Id": str(user_id)},
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == created["id"]


def test_prevents_duplicate_annual_budget_for_same_category(client, user_id) -> None:
    category_id = _create_category(client, user_id, "Trips")

    first = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "period_type": "annual",
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
            "period_type": "annual",
            "currency": "EUR",
            "amount": "1200.00",
        },
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Ya existe un presupuesto anual para esta categoría"


def test_monthly_and_annual_budget_can_coexist_for_same_category(client, user_id) -> None:
    category_id = _create_category(client, user_id, "Leisure")

    monthly = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "period_type": "monthly",
            "currency": "EUR",
            "amount": "80.00",
        },
    )
    assert monthly.status_code == 201

    annual = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "period_type": "annual",
            "currency": "EUR",
            "amount": "900.00",
        },
    )
    assert annual.status_code == 201

    list_response = client.get("/api/v1/budgets", headers={"X-User-Id": str(user_id)})
    assert list_response.json()["total"] == 2


def test_update_budget_amount(client, user_id) -> None:
    category_id = _create_category(client, user_id, "Cafe")

    created = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "period_type": "monthly",
            "currency": "EUR",
            "amount": "20.00",
        },
    )
    assert created.status_code == 201
    budget_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/budgets/{budget_id}",
        headers={"X-User-Id": str(user_id)},
        json={"amount": "35.00"},
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == "35.00"
