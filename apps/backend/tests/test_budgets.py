import uuid

from conftest import TestingSessionLocal

from app.models.transaction import Transaction


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


def test_batch_delete_budgets(client, user_id) -> None:
    ids: list[str] = []
    for name in ("Gym", "Books", "Music"):
        category_id = _create_category(client, user_id, name)
        created = client.post(
            "/api/v1/budgets",
            headers={"X-User-Id": str(user_id)},
            json={
                "category_id": category_id,
                "period_type": "monthly",
                "currency": "EUR",
                "amount": "30.00",
            },
        )
        assert created.status_code == 201
        ids.append(created.json()["id"])

    response = client.post(
        "/api/v1/budgets/batch-delete",
        headers={"X-User-Id": str(user_id)},
        json={"budget_ids": ids[:2]},
    )
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2

    remaining = client.get("/api/v1/budgets", headers={"X-User-Id": str(user_id)})
    assert remaining.json()["total"] == 1
    assert remaining.json()["items"][0]["id"] == ids[2]


def test_reorder_budgets(client, user_id) -> None:
    ids: list[str] = []
    for name in ("Alpha", "Beta", "Gamma"):
        category_id = _create_category(client, user_id, name)
        created = client.post(
            "/api/v1/budgets",
            headers={"X-User-Id": str(user_id)},
            json={
                "category_id": category_id,
                "period_type": "monthly",
                "currency": "EUR",
                "amount": "10.00",
            },
        )
        assert created.status_code == 201
        ids.append(created.json()["id"])

    new_order = [ids[2], ids[0], ids[1]]
    response = client.post(
        "/api/v1/budgets/reorder",
        headers={"X-User-Id": str(user_id)},
        json={"budget_ids": new_order},
    )
    assert response.status_code == 204

    listed = client.get(
        "/api/v1/budgets?sort_by=position&sort_order=asc",
        headers={"X-User-Id": str(user_id)},
    )
    assert [item["id"] for item in listed.json()["items"]] == new_order
    assert [item["position"] for item in listed.json()["items"]] == [0, 1, 2]


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


def _create_account(client, user_id, name: str = "Main Account") -> str:
    response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={"name": name, "type": "checking", "currency": "EUR"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_transaction(
    client,
    user_id,
    *,
    account_id: str,
    category_id: str | None,
    date: str,
    amount: str,
    description: str = "Test transaction",
) -> str:
    response = client.post(
        "/api/v1/transactions",
        headers={"X-User-Id": str(user_id)},
        json={
            "account_id": account_id,
            "category_id": category_id,
            "date": date,
            "amount": amount,
            "currency": "EUR",
            "description": description,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _get_spend(client, user_id, year: int) -> dict:
    response = client.get(
        f"/api/v1/budgets/spend?year={year}",
        headers={"X-User-Id": str(user_id)},
    )
    assert response.status_code == 200
    return response.json()


def test_spend_aggregates_per_category_and_month(client, user_id) -> None:
    account_id = _create_account(client, user_id)
    food_id = _create_category(client, user_id, "Food")
    travel_id = _create_category(client, user_id, "Travel")

    _create_transaction(
        client,
        user_id,
        account_id=account_id,
        category_id=food_id,
        date="2026-01-10",
        amount="-50.00",
    )
    _create_transaction(
        client,
        user_id,
        account_id=account_id,
        category_id=food_id,
        date="2026-01-20",
        amount="-25.50",
    )
    _create_transaction(
        client,
        user_id,
        account_id=account_id,
        category_id=food_id,
        date="2026-03-05",
        amount="-10.00",
    )
    _create_transaction(
        client,
        user_id,
        account_id=account_id,
        category_id=travel_id,
        date="2026-03-15",
        amount="-200.00",
    )

    payload = _get_spend(client, user_id, 2026)
    assert payload["year"] == 2026

    by_key = {(item["category_id"], item["month"]): item["spent"] for item in payload["items"]}
    assert by_key == {
        (food_id, 1): "75.50",
        (food_id, 3): "10.00",
        (travel_id, 3): "200.00",
    }


def test_spend_filters_by_year(client, user_id) -> None:
    account_id = _create_account(client, user_id)
    category_id = _create_category(client, user_id, "Food")

    _create_transaction(
        client,
        user_id,
        account_id=account_id,
        category_id=category_id,
        date="2025-12-31",
        amount="-99.00",
    )
    _create_transaction(
        client,
        user_id,
        account_id=account_id,
        category_id=category_id,
        date="2026-01-01",
        amount="-40.00",
    )
    _create_transaction(
        client,
        user_id,
        account_id=account_id,
        category_id=category_id,
        date="2027-01-01",
        amount="-77.00",
    )

    payload = _get_spend(client, user_id, 2026)
    assert payload["items"] == [{"category_id": category_id, "month": 1, "spent": "40.00"}]


def test_spend_excludes_transfers(client, user_id) -> None:
    from_account_id = _create_account(client, user_id, "From Account")
    to_account_id = _create_account(client, user_id, "To Account")
    category_id = _create_category(client, user_id, "Food")

    # Regular expense that should count.
    _create_transaction(
        client,
        user_id,
        account_id=from_account_id,
        category_id=category_id,
        date="2026-02-10",
        amount="-30.00",
    )

    # Transfer legs (no category, transfer_group_id set) must not count.
    transfer = client.post(
        "/api/v1/transactions/transfer",
        headers={"X-User-Id": str(user_id)},
        json={
            "from_account_id": from_account_id,
            "to_account_id": to_account_id,
            "date": "2026-02-11",
            "amount": "500.00",
            "description": "Monthly transfer",
        },
    )
    assert transfer.status_code == 201

    # An expense-category transaction that is part of a transfer group must
    # also be excluded.
    grouped_id = _create_transaction(
        client,
        user_id,
        account_id=from_account_id,
        category_id=category_id,
        date="2026-02-12",
        amount="-80.00",
    )
    with TestingSessionLocal() as db:
        transaction = db.get(Transaction, uuid.UUID(grouped_id))
        assert transaction is not None
        transaction.transfer_group_id = uuid.uuid4()
        db.commit()

    payload = _get_spend(client, user_id, 2026)
    assert payload["items"] == [{"category_id": category_id, "month": 2, "spent": "30.00"}]


def test_spend_nets_refunds_and_floors_at_zero(client, user_id) -> None:
    account_id = _create_account(client, user_id)
    category_id = _create_category(client, user_id, "Shopping")

    # January: 100 spent, 30 refunded -> 70 net.
    _create_transaction(
        client,
        user_id,
        account_id=account_id,
        category_id=category_id,
        date="2026-01-05",
        amount="-100.00",
    )
    _create_transaction(
        client,
        user_id,
        account_id=account_id,
        category_id=category_id,
        date="2026-01-15",
        amount="30.00",
    )
    # February: refund exceeds spend -> floored at 0 and omitted.
    _create_transaction(
        client,
        user_id,
        account_id=account_id,
        category_id=category_id,
        date="2026-02-05",
        amount="-20.00",
    )
    _create_transaction(
        client,
        user_id,
        account_id=account_id,
        category_id=category_id,
        date="2026-02-20",
        amount="50.00",
    )

    payload = _get_spend(client, user_id, 2026)
    assert payload["items"] == [{"category_id": category_id, "month": 1, "spent": "70.00"}]


def test_spend_route_does_not_collide_with_get_by_id(client, user_id) -> None:
    category_id = _create_category(client, user_id, "Housing")
    created = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": category_id,
            "period_type": "monthly",
            "currency": "EUR",
            "amount": "1200.00",
        },
    )
    assert created.status_code == 201
    budget_id = created.json()["id"]

    spend_response = client.get(
        "/api/v1/budgets/spend?year=2026",
        headers={"X-User-Id": str(user_id)},
    )
    assert spend_response.status_code == 200
    assert spend_response.json() == {"year": 2026, "items": []}

    by_id = client.get(
        f"/api/v1/budgets/{budget_id}",
        headers={"X-User-Id": str(user_id)},
    )
    assert by_id.status_code == 200
    assert by_id.json()["id"] == budget_id


def test_spend_requires_valid_year(client, user_id) -> None:
    missing = client.get("/api/v1/budgets/spend", headers={"X-User-Id": str(user_id)})
    assert missing.status_code == 422

    out_of_range = client.get(
        "/api/v1/budgets/spend?year=1999",
        headers={"X-User-Id": str(user_id)},
    )
    assert out_of_range.status_code == 422
