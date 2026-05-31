def _create_holding(client, user_id, **overrides) -> dict:
    payload = {
        "asset_name": "Vanguard All-World",
        "asset_symbol": "VWCE",
        "asset_type": "etf",
        "quantity": "10",
        "average_buy_price": "100.0000",
        "currency": "EUR",
    }
    payload.update(overrides)
    response = client.post(
        "/api/v1/portfolio/holdings",
        headers={"X-User-Id": str(user_id)},
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_list_holdings(client, user_id) -> None:
    _create_holding(client, user_id)

    listed = client.get("/api/v1/portfolio/holdings", headers={"X-User-Id": str(user_id)})
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert payload["items"][0]["asset_symbol"] == "VWCE"


def test_portfolio_summary_value_and_allocation(client, user_id) -> None:
    etf = _create_holding(client, user_id)
    crypto = _create_holding(
        client,
        user_id,
        asset_name="Bitcoin",
        asset_symbol="BTC",
        asset_type="crypto",
        quantity="0.5",
        average_buy_price="40000.0000",
    )

    # Set a current price only for the ETF: 10 * 110 = 1100 (invested was 1000).
    price_response = client.post(
        f"/api/v1/portfolio/holdings/{etf['id']}/price",
        headers={"X-User-Id": str(user_id)},
        json={"price": "110.0000"},
    )
    assert price_response.status_code == 200

    summary = client.get("/api/v1/portfolio/summary", headers={"X-User-Id": str(user_id)})
    assert summary.status_code == 200
    data = summary.json()

    by_id = {item["id"]: item for item in data["holdings"]}
    etf_row = by_id[etf["id"]]
    crypto_row = by_id[crypto["id"]]

    assert etf_row["invested"] == "1000.00"
    assert etf_row["current_value"] == "1100.00"
    assert etf_row["unrealized_pnl"] == "100.00"

    # Crypto has no price yet: value falls back to invested, pnl is unknown.
    assert crypto_row["current_value"] is None
    assert crypto_row["unrealized_pnl"] is None

    assert data["total_invested"] == "21000.00"
    assert data["total_value"] == "21100.00"
    assert data["total_unrealized_pnl"] == "100.00"

    allocation_sum = round(etf_row["allocation_pct"] + crypto_row["allocation_pct"], 0)
    assert allocation_sum == 100


def test_update_price_requires_symbol(client, user_id) -> None:
    holding = _create_holding(client, user_id, asset_symbol=None, asset_name="Oro físico")

    response = client.post(
        f"/api/v1/portfolio/holdings/{holding['id']}/price",
        headers={"X-User-Id": str(user_id)},
        json={"price": "60.0000"},
    )
    assert response.status_code == 400


def test_delete_holding(client, user_id) -> None:
    holding = _create_holding(client, user_id)

    deleted = client.delete(
        f"/api/v1/portfolio/holdings/{holding['id']}",
        headers={"X-User-Id": str(user_id)},
    )
    assert deleted.status_code == 204

    listed = client.get("/api/v1/portfolio/holdings", headers={"X-User-Id": str(user_id)})
    assert listed.json()["total"] == 0


def test_refresh_prices_updates_crypto_via_provider(client, user_id, monkeypatch) -> None:
    from decimal import Decimal

    from app.services import price_fetch_service

    headers = {"X-User-Id": str(user_id)}
    holding = _create_holding(
        client,
        user_id,
        asset_name="Bitcoin",
        asset_symbol="BTC",
        asset_type="crypto",
        quantity="2",
        average_buy_price="30000.0000",
    )

    monkeypatch.setattr(
        price_fetch_service.CoinGeckoProvider,
        "fetch_price",
        lambda self, *, symbol, currency: Decimal("50000"),
    )

    response = client.post("/api/v1/portfolio/prices/refresh", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["updated"]) == 1
    assert body["updated"][0]["asset"] == "BTC"

    summary = client.get("/api/v1/portfolio/summary", headers=headers).json()
    row = next(item for item in summary["holdings"] if item["id"] == holding["id"])
    assert row["current_price"] == "50000.0000"
    assert row["current_value"] == "100000.00"


def test_refresh_prices_reports_missing_stock_provider(client, user_id) -> None:
    headers = {"X-User-Id": str(user_id)}
    _create_holding(
        client,
        user_id,
        asset_name="Apple",
        asset_symbol="AAPL",
        asset_type="stock",
        quantity="5",
        average_buy_price="150.0000",
    )

    response = client.post("/api/v1/portfolio/prices/refresh", headers=headers)
    assert response.status_code == 200
    failed = response.json()["failed"]
    assert any(item["asset"] == "AAPL" for item in failed)
