def _create_category(client, user_id, name: str) -> str:
    response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={"name": name, "type": "expense", "color": "#0f766e", "icon": "cart"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_account(client, user_id) -> str:
    response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={"name": "Cuenta", "bank_name": "X", "type": "checking", "currency": "EUR"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_rule_crud(client, user_id) -> None:
    headers = {"X-User-Id": str(user_id)}
    category_id = _create_category(client, user_id, "Supermercado")

    created = client.post(
        "/api/v1/categorization-rules",
        headers=headers,
        json={"category_id": category_id, "match_type": "contains", "pattern": "mercadona"},
    )
    assert created.status_code == 201
    rule_id = created.json()["id"]

    listed = client.get("/api/v1/categorization-rules", headers=headers)
    assert listed.json()["total"] == 1

    deleted = client.delete(f"/api/v1/categorization-rules/{rule_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/api/v1/categorization-rules", headers=headers).json()["total"] == 0


def test_rule_autocategorizes_new_transaction(client, user_id) -> None:
    headers = {"X-User-Id": str(user_id)}
    category_id = _create_category(client, user_id, "Supermercado")
    account_id = _create_account(client, user_id)

    client.post(
        "/api/v1/categorization-rules",
        headers=headers,
        json={"category_id": category_id, "match_type": "contains", "pattern": "MERCADONA"},
    )

    created = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": account_id,
            "category_id": None,
            "date": "2026-03-01",
            "amount": "-42.10",
            "currency": "EUR",
            "description": "Compra MERCADONA 1234",
        },
    )
    assert created.status_code == 201
    assert created.json()["category_id"] == category_id


def test_rule_does_not_override_explicit_category(client, user_id) -> None:
    headers = {"X-User-Id": str(user_id)}
    rule_category = _create_category(client, user_id, "Supermercado")
    explicit_category = _create_category(client, user_id, "Ocio")
    account_id = _create_account(client, user_id)

    client.post(
        "/api/v1/categorization-rules",
        headers=headers,
        json={"category_id": rule_category, "match_type": "contains", "pattern": "mercadona"},
    )

    created = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": account_id,
            "category_id": explicit_category,
            "date": "2026-03-01",
            "amount": "-10.00",
            "currency": "EUR",
            "description": "MERCADONA pero ocio",
        },
    )
    assert created.status_code == 201
    assert created.json()["category_id"] == explicit_category
