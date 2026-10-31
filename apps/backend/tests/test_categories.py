def test_create_and_list_categories(client, user_id) -> None:
    response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Groceries",
            "type": "expense",
            "color": "#22c55e",
            "icon": "shopping-cart",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Groceries"
    assert created["type"] == "expense"

    list_response = client.get(
        "/api/v1/categories?category_type=expense",
        headers={"X-User-Id": str(user_id)},
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["name"] == "Groceries"


def test_prevents_duplicate_category_name_and_type(client, user_id) -> None:
    first = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Salary",
            "type": "income",
            "color": "#2563eb",
            "icon": "wallet",
        },
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Salary",
            "type": "income",
            "color": "#1d4ed8",
            "icon": "wallet-2",
        },
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "A category with the same name and type already exists"


def test_prevents_duplicate_category_name_and_type_on_update(client, user_id) -> None:
    first = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Rent",
            "type": "expense",
            "color": "#2563eb",
            "icon": "house",
        },
    )
    second = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Travel",
            "type": "expense",
            "color": "#0f766e",
            "icon": "plane",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201

    duplicate_update = client.patch(
        f"/api/v1/categories/{second.json()['id']}",
        headers={"X-User-Id": str(user_id)},
        json={"name": "Rent"},
    )

    assert duplicate_update.status_code == 409
    assert (
        duplicate_update.json()["detail"] == "A category with the same name and type already exists"
    )
