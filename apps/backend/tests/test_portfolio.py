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


def test_add_contribution_updates_quantity_and_average(client, user_id) -> None:
    from decimal import Decimal

    from conftest import TestingSessionLocal

    from app.models.trade import Trade

    headers = {"X-User-Id": str(user_id)}
    holding = _create_holding(client, user_id)  # 10 uds @ 100.0000 EUR

    response = client.post(
        f"/api/v1/portfolio/holdings/{holding['id']}/contribution",
        headers=headers,
        json={"amount": "200.00", "price": "200.0000", "date": "2026-07-05"},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    # shares = 200 / 200 = 1.00000000; new_avg = (10*100 + 200) / 11 = 109.0909
    assert Decimal(body["quantity"]) == Decimal("11")
    assert Decimal(body["average_buy_price"]) == Decimal("109.0909")

    with TestingSessionLocal() as db:
        trades = db.query(Trade).filter(Trade.user_id == user_id).all()
        assert len(trades) == 1
        trade = trades[0]
        assert trade.side.value == "buy"
        assert trade.asset_symbol == "VWCE"
        assert trade.quantity == Decimal("1.00000000")
        assert trade.price == Decimal("200.0000")
        assert trade.fees == Decimal("0")
        assert trade.currency == "EUR"
        assert str(trade.holding_id) == holding["id"]
        assert trade.date.isoformat() == "2026-07-05"

    # The contribution price is recorded so the position values at that price.
    summary = client.get("/api/v1/portfolio/summary", headers=headers).json()
    row = next(item for item in summary["holdings"] if item["id"] == holding["id"])
    assert Decimal(row["current_price"]) == Decimal("200")
    assert row["current_value"] == "2200.00"


def test_add_contribution_uneven_amount_quantizes(client, user_id) -> None:
    from decimal import Decimal

    headers = {"X-User-Id": str(user_id)}
    holding = _create_holding(client, user_id)  # 10 uds @ 100.0000 EUR

    response = client.post(
        f"/api/v1/portfolio/holdings/{holding['id']}/contribution",
        headers=headers,
        json={"amount": "75.00", "price": "41.0000"},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    # shares = 75 / 41 = 1.82926829 (8 decimals)
    # new_avg = (10*100 + 75) / 11.82926829 = 90.8763 (4 decimals)
    assert Decimal(body["quantity"]) == Decimal("11.82926829")
    assert Decimal(body["average_buy_price"]) == Decimal("90.8763")


def test_add_contribution_rejects_invalid_amount_and_price(client, user_id) -> None:
    headers = {"X-User-Id": str(user_id)}
    holding = _create_holding(client, user_id)

    for payload in (
        {"amount": "0", "price": "100.0000"},
        {"amount": "-5", "price": "100.0000"},
        {"amount": "100.00", "price": "0"},
        {"amount": "100.00", "price": "-1"},
    ):
        response = client.post(
            f"/api/v1/portfolio/holdings/{holding['id']}/contribution",
            headers=headers,
            json=payload,
        )
        assert response.status_code == 422, payload


def test_add_contribution_unknown_holding(client, user_id) -> None:
    import uuid as uuid_module

    response = client.post(
        f"/api/v1/portfolio/holdings/{uuid_module.uuid4()}/contribution",
        headers={"X-User-Id": str(user_id)},
        json={"amount": "100.00", "price": "50.0000"},
    )
    assert response.status_code == 404


def test_add_contribution_requires_symbol(client, user_id) -> None:
    holding = _create_holding(client, user_id, asset_symbol=None, asset_name="Oro físico")

    response = client.post(
        f"/api/v1/portfolio/holdings/{holding['id']}/contribution",
        headers={"X-User-Id": str(user_id)},
        json={"amount": "100.00", "price": "50.0000"},
    )
    assert response.status_code == 400


class _FakeHTTPResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> object:
        return self._payload


def _patch_twelvedata_http(monkeypatch, quotes: dict[str, object]) -> list[str]:
    """Route TwelveData /price calls to canned payloads, recording symbols."""
    import httpx

    from app.services import price_fetch_service

    calls: list[str] = []

    def fake_get(url, *, params, timeout):  # noqa: ANN001, ANN202
        symbol = params["symbol"]
        calls.append(symbol)
        payload = quotes.get(symbol)
        if payload is Exception:
            raise httpx.ConnectError("boom")
        return _FakeHTTPResponse(payload)

    monkeypatch.setattr(price_fetch_service.httpx, "get", fake_get)
    return calls


def test_twelvedata_usd_holding_skips_fx(monkeypatch) -> None:
    from decimal import Decimal

    from app.services.price_fetch_service import TwelveDataProvider

    calls = _patch_twelvedata_http(monkeypatch, {"AAPL": {"price": "150.25"}})
    provider = TwelveDataProvider("key")

    price = provider.fetch_price(symbol="AAPL", currency="USD")

    assert price == Decimal("150.25")
    assert calls == ["AAPL"]


def test_twelvedata_converts_to_holding_currency(monkeypatch) -> None:
    from decimal import Decimal

    from app.services.price_fetch_service import TwelveDataProvider

    calls = _patch_twelvedata_http(
        monkeypatch,
        {"VWCE": {"price": "100"}, "USD/EUR": {"price": "0.9"}},
    )
    provider = TwelveDataProvider("key")

    price = provider.fetch_price(symbol="VWCE", currency="EUR")

    assert price == Decimal("90.0")
    assert calls == ["VWCE", "USD/EUR"]


def test_twelvedata_returns_none_when_fx_pair_fails(monkeypatch) -> None:
    from app.services.price_fetch_service import TwelveDataProvider

    # Pair endpoint raises a connection error.
    _patch_twelvedata_http(monkeypatch, {"VWCE": {"price": "100"}, "USD/EUR": Exception})
    assert TwelveDataProvider("key").fetch_price(symbol="VWCE", currency="EUR") is None


def test_twelvedata_returns_none_when_fx_pair_has_no_price(monkeypatch) -> None:
    from app.services.price_fetch_service import TwelveDataProvider

    # Pair endpoint answers without a usable price (e.g. an error payload).
    _patch_twelvedata_http(
        monkeypatch,
        {"VWCE": {"price": "100"}, "USD/EUR": {"code": 404, "message": "not found"}},
    )
    assert TwelveDataProvider("key").fetch_price(symbol="VWCE", currency="EUR") is None
