from app.core.config import settings


def test_auth_providers_default_to_local_password(client) -> None:
    original_auth_mode = settings.auth_mode
    original_google_client_id = settings.google_oauth_client_id
    original_google_client_secret = settings.google_oauth_client_secret
    original_google_redirect_uri = settings.google_oauth_redirect_uri
    original_client_id = settings.entra_client_id
    original_client_secret = settings.entra_client_secret
    original_authority_url = settings.entra_authority_url
    original_metadata_url = settings.entra_metadata_url

    settings.auth_mode = "local"
    settings.google_oauth_client_id = None
    settings.google_oauth_client_secret = None
    settings.google_oauth_redirect_uri = ""
    settings.entra_client_id = None
    settings.entra_client_secret = None
    settings.entra_authority_url = None
    settings.entra_metadata_url = None

    try:
        response = client.get("/api/v1/auth/providers")
    finally:
        settings.auth_mode = original_auth_mode
        settings.google_oauth_client_id = original_google_client_id
        settings.google_oauth_client_secret = original_google_client_secret
        settings.google_oauth_redirect_uri = original_google_redirect_uri
        settings.entra_client_id = original_client_id
        settings.entra_client_secret = original_client_secret
        settings.entra_authority_url = original_authority_url
        settings.entra_metadata_url = original_metadata_url

    assert response.status_code == 200
    assert response.json() == {
        "local_password_enabled": True,
        "entra_external_id_enabled": False,
        "google_enabled": False,
    }


def test_entra_start_requires_external_id_configuration(client) -> None:
    original_auth_mode = settings.auth_mode
    original_client_id = settings.entra_client_id
    original_client_secret = settings.entra_client_secret
    original_authority_url = settings.entra_authority_url
    original_metadata_url = settings.entra_metadata_url

    settings.auth_mode = "entra_external_id"
    settings.entra_client_id = None
    settings.entra_client_secret = None
    settings.entra_authority_url = None
    settings.entra_metadata_url = None

    try:
        response = client.get("/api/v1/auth/entra/start")
    finally:
        settings.auth_mode = original_auth_mode
        settings.entra_client_id = original_client_id
        settings.entra_client_secret = original_client_secret
        settings.entra_authority_url = original_authority_url
        settings.entra_metadata_url = original_metadata_url

    assert response.status_code == 503
    assert response.json()["detail"] == "Microsoft Entra External ID is not configured"


def test_google_start_requires_google_configuration(client) -> None:
    original_client_id = settings.google_oauth_client_id
    original_client_secret = settings.google_oauth_client_secret
    original_redirect_uri = settings.google_oauth_redirect_uri

    settings.google_oauth_client_id = None
    settings.google_oauth_client_secret = None
    settings.google_oauth_redirect_uri = ""

    try:
        response = client.get("/api/v1/auth/google/start")
    finally:
        settings.google_oauth_client_id = original_client_id
        settings.google_oauth_client_secret = original_client_secret
        settings.google_oauth_redirect_uri = original_redirect_uri

    assert response.status_code == 503
    assert response.json()["detail"] == "Google OAuth is not configured"


def test_register_sets_session_and_returns_user(client) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new-user@example.com",
            "name": "New User",
            "password": "supersecret123",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == "new-user@example.com"
    assert payload["name"] == "New User"
    assert "finance_foundation_session" in response.headers.get("set-cookie", "")

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "new-user@example.com"


def test_login_and_logout_flow(client) -> None:
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "login-user@example.com",
            "name": "Login User",
            "password": "anothersecret123",
        },
    )
    assert register.status_code == 201

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    unauthenticated = client.get("/api/v1/auth/me")
    assert unauthenticated.status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login-user@example.com",
            "password": "anothersecret123",
        },
    )
    assert login.status_code == 200

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "login-user@example.com"


def test_login_rejects_invalid_credentials(client) -> None:
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "bad-login@example.com",
            "name": "Bad Login",
            "password": "yetanothersecret123",
        },
    )
    assert register.status_code == 201

    client.post("/api/v1/auth/logout")

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "bad-login@example.com",
            "password": "wrong-password",
        },
    )
    assert login.status_code == 401
    assert login.json()["detail"] == "Invalid email or password"


def test_delete_current_account_removes_session_and_user(client) -> None:
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "delete-me@example.com",
            "name": "Delete Me",
            "password": "permanentsecret123",
        },
    )
    assert register.status_code == 201

    delete_response = client.delete("/api/v1/auth/me")
    assert delete_response.status_code == 204

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "delete-me@example.com",
            "password": "permanentsecret123",
        },
    )
    assert login.status_code == 401
