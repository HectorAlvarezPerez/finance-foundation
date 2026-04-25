def test_create_and_list_accounts(client, user_id) -> None:
    response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Main Account",
            "bank_name": "Santander",
            "type": "checking",
            "currency": "EUR",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Main Account"
    assert created["bank_name"] == "Santander"
    assert created["type"] == "checking"

    list_response = client.get(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["name"] == "Main Account"
    assert payload["items"][0]["bank_name"] == "Santander"


def test_update_account_details(client, user_id) -> None:
    create_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Main Account",
            "bank_name": "Santander",
            "type": "checking",
            "currency": "EUR",
        },
    )

    assert create_response.status_code == 201
    account_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/accounts/{account_id}",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Cuenta nómina",
            "bank_name": "BBVA",
            "currency": "USD",
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Cuenta nómina"
    assert updated["bank_name"] == "BBVA"
    assert updated["currency"] == "USD"


def test_create_brokerage_account(client, user_id) -> None:
    response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Trade Republic",
            "type": "brokerage",
            "currency": "EUR",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["type"] == "brokerage"


def test_create_account_with_initial_balance_creates_opening_transaction(client, user_id) -> None:
    response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Savings Pot",
            "type": "savings",
            "currency": "EUR",
            "initial_balance": "250.00",
        },
    )

    assert response.status_code == 201
    account_id = response.json()["id"]

    transactions_response = client.get(
        "/api/v1/transactions?limit=100",
        headers={"X-User-Id": str(user_id)},
    )

    assert transactions_response.status_code == 200
    payload = transactions_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["account_id"] == account_id
    assert payload["items"][0]["description"] == "Saldo inicial"
    assert payload["items"][0]["amount"] == "250.00"


def test_delete_account_removes_related_transactions(client, user_id) -> None:
    create_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Temporary Account",
            "bank_name": "N26",
            "type": "checking",
            "currency": "EUR",
            "initial_balance": "125.00",
        },
    )

    assert create_response.status_code == 201
    account_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/api/v1/accounts/{account_id}",
        headers={"X-User-Id": str(user_id)},
    )

    assert delete_response.status_code == 204

    accounts_response = client.get(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
    )
    assert accounts_response.status_code == 200
    assert accounts_response.json()["total"] == 0

    transactions_response = client.get(
        "/api/v1/transactions?limit=100",
        headers={"X-User-Id": str(user_id)},
    )
    assert transactions_response.status_code == 200
    assert transactions_response.json()["total"] == 0
