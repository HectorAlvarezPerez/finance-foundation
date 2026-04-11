from fastapi.testclient import TestClient

from app.main import app
from app.services import health_service

client = TestClient(app)


def test_healthcheck_returns_ok() -> None:
    original = health_service.get_health_status
    health_service.get_health_status = lambda: (True, "ok")
    try:
        response = client.get("/api/v1/health")
    finally:
        health_service.get_health_status = original

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok"}}


def test_healthcheck_returns_service_unavailable_when_schema_is_incompatible() -> None:
    original = health_service.get_health_status
    health_service.get_health_status = lambda: (False, "database schema is not up to date")
    try:
        response = client.get("/api/v1/health")
    finally:
        health_service.get_health_status = original

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "checks": {"database": "database schema is not up to date"},
    }
