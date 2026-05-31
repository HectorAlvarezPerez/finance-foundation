from decimal import Decimal

from app.services.fx_service import CurrencyConverter


def test_currency_converter_direct_inverse_and_missing() -> None:
    converter = CurrencyConverter({("USD", "EUR"): Decimal("0.9")})

    assert converter.convert(Decimal("100"), "EUR", "EUR") == Decimal("100")
    assert converter.convert(Decimal("100"), "USD", "EUR") == Decimal("90.0")
    # Inverse: 1 USD = 0.9 EUR  =>  1 EUR = 1/0.9 USD
    assert converter.convert(Decimal("9"), "EUR", "USD") == Decimal("10")
    assert converter.convert(Decimal("100"), "GBP", "EUR") is None


def test_fx_rates_crud(client, user_id) -> None:
    created = client.post(
        "/api/v1/fx/rates",
        headers={"X-User-Id": str(user_id)},
        json={"from_currency": "usd", "to_currency": "eur", "rate": "0.9"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["from_currency"] == "USD"
    assert body["to_currency"] == "EUR"

    listed = client.get("/api/v1/fx/rates", headers={"X-User-Id": str(user_id)})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    deleted = client.delete(
        f"/api/v1/fx/rates/{body['id']}",
        headers={"X-User-Id": str(user_id)},
    )
    assert deleted.status_code == 204
    assert client.get("/api/v1/fx/rates", headers={"X-User-Id": str(user_id)}).json()["total"] == 0


def test_fx_rate_rejects_same_currency(client, user_id) -> None:
    response = client.post(
        "/api/v1/fx/rates",
        headers={"X-User-Id": str(user_id)},
        json={"from_currency": "EUR", "to_currency": "EUR", "rate": "1"},
    )
    assert response.status_code == 400


def test_portfolio_totals_use_base_currency(client, user_id) -> None:
    headers = {"X-User-Id": str(user_id)}
    client.put(
        "/api/v1/settings",
        headers=headers,
        json={"default_currency": "EUR", "locale": "es-ES", "theme": "light"},
    )

    holding = client.post(
        "/api/v1/portfolio/holdings",
        headers=headers,
        json={
            "asset_name": "Apple",
            "asset_symbol": "AAPL",
            "asset_type": "stock",
            "quantity": "10",
            "average_buy_price": "100.0000",
            "currency": "USD",
        },
    ).json()
    client.post(
        f"/api/v1/portfolio/holdings/{holding['id']}/price",
        headers=headers,
        json={"price": "100.0000"},
    )
    client.post(
        "/api/v1/fx/rates",
        headers=headers,
        json={"from_currency": "USD", "to_currency": "EUR", "rate": "0.9"},
    )

    summary = client.get("/api/v1/portfolio/summary", headers=headers).json()
    # Per-holding stays in USD; totals/allocation use EUR base.
    row = summary["holdings"][0]
    assert row["current_value"] == "1000.00"
    assert summary["total_value"] == "900.00"
    assert row["allocation_pct"] == 100.0
