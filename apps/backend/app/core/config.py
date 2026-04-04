from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "finance-foundation-backend"
    app_env: str = "development"
    auth_mode: Literal["local", "entra_external_id"] = "local"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/finance_foundation"
    session_secret_key: str = "dev-session-secret-change-me"
    session_cookie_name: str = "finance_foundation_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_cookie_max_age: int = 60 * 60 * 24 * 7
    auth_state_max_age: int = 60 * 10
    allow_dev_user_header: bool = True
    frontend_origin: str = "http://localhost:3000,http://localhost:3100"
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    google_oauth_metadata_url: str = "https://accounts.google.com/.well-known/openid-configuration"
    entra_client_id: str | None = None
    entra_client_secret: str | None = None
    entra_authority_url: str | None = None
    entra_metadata_url: str | None = None
    entra_redirect_uri: str = "http://localhost:8000/api/v1/auth/entra/callback"
    entra_google_domain_hint: str | None = "google.com"
    azure_document_intelligence_endpoint: str | None = None
    azure_document_intelligence_api_key: str | None = None
    azure_document_intelligence_model_id: str = "prebuilt-layout"
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_pdf_parser_deployment: str | None = None
    azure_openai_api_version: str = "2025-03-01-preview"

    @property
    def frontend_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]

    @property
    def default_frontend_origin(self) -> str:
        return self.frontend_origins[0] if self.frontend_origins else "http://localhost:3000"

    @property
    def entra_openid_configuration_url(self) -> str | None:
        if self.entra_metadata_url:
            return self.entra_metadata_url

        if self.entra_authority_url:
            return f"{self.entra_authority_url.rstrip('/')}/.well-known/openid-configuration"

        return None

    @property
    def entra_external_id_enabled(self) -> bool:
        return all(
            [
                self.auth_mode == "entra_external_id",
                self.entra_client_id,
                self.entra_client_secret,
                self.entra_redirect_uri,
                self.entra_openid_configuration_url,
            ]
        )

    @property
    def google_oauth_enabled(self) -> bool:
        return all(
            [
                self.google_oauth_client_id,
                self.google_oauth_client_secret,
                self.google_oauth_redirect_uri,
                self.google_oauth_metadata_url,
            ]
        )

    @property
    def azure_document_intelligence_enabled(self) -> bool:
        return bool(
            self.azure_document_intelligence_endpoint
            and self.azure_document_intelligence_api_key
            and self.azure_document_intelligence_model_id
        )

    @property
    def azure_openai_pdf_parser_enabled(self) -> bool:
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and self.azure_openai_pdf_parser_deployment
            and self.azure_openai_api_version
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
