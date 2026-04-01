def test_upsert_and_get_settings(client, user_id) -> None:
    put_response = client.put(
        "/api/v1/settings",
        headers={"X-User-Id": str(user_id)},
        json={
            "default_currency": "EUR",
            "locale": "es-ES",
            "theme": "system",
        },
    )

    assert put_response.status_code == 200
    created = put_response.json()
    assert created["default_currency"] == "EUR"
    assert created["locale"] == "es-ES"
    assert created["theme"] == "system"

    get_response = client.get(
        "/api/v1/settings",
        headers={"X-User-Id": str(user_id)},
    )

    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["default_currency"] == "EUR"
    assert fetched["locale"] == "es-ES"


def test_get_settings_returns_not_found_before_creation(client, user_id) -> None:
    response = client.get(
        "/api/v1/settings",
        headers={"X-User-Id": str(user_id)},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Settings not found"
