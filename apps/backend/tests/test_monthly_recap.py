import uuid

from conftest import TestingSessionLocal
from sqlalchemy import select

from app.models.monthly_insight_recap import MonthlyInsightRecap
from app.models.user import User


def _create_user(name: str) -> uuid.UUID:
    user = User(
        auth_provider_user_id=f"test-{uuid.uuid4()}",
        email=f"{name}-{uuid.uuid4()}@example.com",
        name=name,
    )
    with TestingSessionLocal() as db:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id


def _setup_recap_fixture(client, user_id: uuid.UUID) -> dict[str, str]:
    checking_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Cuenta principal",
            "bank_name": "Santander",
            "type": "checking",
            "currency": "EUR",
        },
    )
    checking_id = checking_response.json()["id"]

    food_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Comida",
            "type": "expense",
            "color": "#f97316",
            "icon": "utensils",
        },
    )
    food_id = food_response.json()["id"]

    leisure_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Ocio",
            "type": "expense",
            "color": "#fb7185",
            "icon": "gamepad",
        },
    )
    leisure_id = leisure_response.json()["id"]

    salary_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Salario",
            "type": "income",
            "color": "#16a34a",
            "icon": "briefcase",
        },
    )
    salary_id = salary_response.json()["id"]

    budget_response = client.post(
        "/api/v1/budgets",
        headers={"X-User-Id": str(user_id)},
        json={
            "category_id": food_id,
            "year": 2026,
            "month": 3,
            "currency": "EUR",
            "amount": "300.00",
        },
    )
    assert budget_response.status_code == 201

    for payload in [
        {
            "account_id": checking_id,
            "category_id": salary_id,
            "date": "2026-03-01",
            "amount": "2300.00",
            "currency": "EUR",
            "description": "Nómina marzo",
        },
        {
            "account_id": checking_id,
            "category_id": food_id,
            "date": "2026-03-05",
            "amount": "-89.45",
            "currency": "EUR",
            "description": "Supermercado grande",
        },
        {
            "account_id": checking_id,
            "category_id": leisure_id,
            "date": "2026-03-18",
            "amount": "-54.20",
            "currency": "EUR",
            "description": "Concierto",
        },
        {
            "account_id": checking_id,
            "category_id": food_id,
            "date": "2026-02-06",
            "amount": "-45.00",
            "currency": "EUR",
            "description": "Supermercado febrero",
        },
    ]:
        response = client.post(
            "/api/v1/transactions",
            headers={"X-User-Id": str(user_id)},
            json=payload,
        )
        assert response.status_code == 201

    return {
        "account_id": checking_id,
        "food_id": food_id,
    }


def test_monthly_recap_generates_persists_and_reuses_cache(client, user_id) -> None:
    _setup_recap_fixture(client, user_id)

    summary_response = client.get(
        "/api/v1/insights/summary",
        headers={"X-User-Id": str(user_id)},
    )
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["available_recap_months"][0]["month_key"] == "2026-03"

    recap_response = client.get(
        "/api/v1/insights/monthly-recap?month_key=2026-03",
        headers={"X-User-Id": str(user_id)},
    )

    assert recap_response.status_code == 200
    payload = recap_response.json()
    assert payload["status"] in {"ready", "fallback"}
    assert payload["is_stale"] is False
    assert len(payload["stories"]) == 3

    cached_response = client.get(
        "/api/v1/insights/monthly-recap?month_key=2026-03",
        headers={"X-User-Id": str(user_id)},
    )
    assert cached_response.status_code == 200
    assert cached_response.json()["generated_at"] == payload["generated_at"]

    with TestingSessionLocal() as db:
        persisted = db.scalar(
            select(MonthlyInsightRecap).where(
                MonthlyInsightRecap.user_id == user_id,
                MonthlyInsightRecap.month_key == "2026-03",
            )
        )
        assert persisted is not None
        assert persisted.status == payload["status"]


def test_monthly_recap_returns_stale_and_regenerates_on_manual_request(client, user_id) -> None:
    fixture = _setup_recap_fixture(client, user_id)

    first_response = client.get(
        "/api/v1/insights/monthly-recap?month_key=2026-03",
        headers={"X-User-Id": str(user_id)},
    )
    assert first_response.status_code == 200
    first_payload = first_response.json()

    create_response = client.post(
        "/api/v1/transactions",
        headers={"X-User-Id": str(user_id)},
        json={
            "account_id": fixture["account_id"],
            "category_id": fixture["food_id"],
            "date": "2026-03-25",
            "amount": "-20.00",
            "currency": "EUR",
            "description": "Cena tardía",
        },
    )
    assert create_response.status_code == 201

    stale_response = client.get(
        "/api/v1/insights/monthly-recap?month_key=2026-03",
        headers={"X-User-Id": str(user_id)},
    )
    assert stale_response.status_code == 200
    stale_payload = stale_response.json()
    assert stale_payload["is_stale"] is True
    assert stale_payload["generated_at"] == first_payload["generated_at"]

    regenerate_response = client.post(
        "/api/v1/insights/monthly-recap/regenerate",
        headers={"X-User-Id": str(user_id)},
        json={"month_key": "2026-03"},
    )
    assert regenerate_response.status_code == 200
    regenerated_payload = regenerate_response.json()
    assert regenerated_payload["is_stale"] is False
    assert regenerated_payload["generated_at"] != first_payload["generated_at"]


def test_monthly_recap_handles_sparse_month_and_validates_month_key(client, user_id) -> None:
    account_response = client.post(
        "/api/v1/accounts",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Cuenta ligera",
            "type": "checking",
            "currency": "EUR",
        },
    )
    account_id = account_response.json()["id"]

    income_category_response = client.post(
        "/api/v1/categories",
        headers={"X-User-Id": str(user_id)},
        json={
            "name": "Bonus",
            "type": "income",
            "color": "#0ea5e9",
            "icon": "sparkles",
        },
    )
    income_category_id = income_category_response.json()["id"]

    transaction_response = client.post(
        "/api/v1/transactions",
        headers={"X-User-Id": str(user_id)},
        json={
            "account_id": account_id,
            "category_id": income_category_id,
            "date": "2026-04-02",
            "amount": "120.00",
            "currency": "EUR",
            "description": "Ingreso puntual",
        },
    )
    assert transaction_response.status_code == 201

    recap_response = client.get(
        "/api/v1/insights/monthly-recap?month_key=2026-04",
        headers={"X-User-Id": str(user_id)},
    )
    assert recap_response.status_code == 200
    assert len(recap_response.json()["stories"]) == 3

    invalid_response = client.get(
        "/api/v1/insights/monthly-recap?month_key=2026-13",
        headers={"X-User-Id": str(user_id)},
    )
    assert invalid_response.status_code == 400

    empty_response = client.get(
        "/api/v1/insights/monthly-recap?month_key=2026-01",
        headers={"X-User-Id": str(user_id)},
    )
    assert empty_response.status_code == 404


def test_monthly_recap_is_user_scoped(client, user_id) -> None:
    _setup_recap_fixture(client, user_id)
    other_user_id = _create_user("Other User")

    first_response = client.get(
        "/api/v1/insights/monthly-recap?month_key=2026-03",
        headers={"X-User-Id": str(user_id)},
    )
    assert first_response.status_code == 200

    other_response = client.get(
        "/api/v1/insights/monthly-recap?month_key=2026-03",
        headers={"X-User-Id": str(other_user_id)},
    )
    assert other_response.status_code == 404
