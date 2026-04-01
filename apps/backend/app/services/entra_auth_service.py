import secrets
from dataclasses import dataclass
from urllib.parse import urlencode, urljoin, urlparse

import httpx
import jwt
from fastapi import HTTPException, Response, status

from app.core.config import settings
from app.core.security import create_auth_state_token, read_auth_state_token
from app.services.auth_service import AuthService


@dataclass
class OIDCMetadata:
    authorization_endpoint: str
    token_endpoint: str
    issuer: str
    jwks_uri: str


@dataclass
class ExternalIdentity:
    provider_user_id: str
    email: str
    name: str


class EntraAuthService:
    def __init__(self, auth_service: AuthService) -> None:
        self.auth_service = auth_service

    def get_provider_availability(self) -> dict[str, bool]:
        return {
            "local_password_enabled": True,
            "entra_external_id_enabled": settings.entra_external_id_enabled,
            "google_enabled": False,
        }

    def build_authorization_url(self, *, next_path: str, provider: str | None = None) -> str:
        self._ensure_configured()
        metadata = self._fetch_metadata()
        nonce = secrets.token_urlsafe(16)
        state = create_auth_state_token(
            {
                "next": self._sanitize_next_path(next_path),
                "nonce": nonce,
            }
        )
        query: dict[str, str] = {
            "client_id": settings.entra_client_id or "",
            "response_type": "code",
            "redirect_uri": settings.entra_redirect_uri,
            "scope": "openid profile email",
            "response_mode": "query",
            "state": state,
            "nonce": nonce,
        }

        if provider == "google" and settings.entra_google_domain_hint:
            query["domain_hint"] = settings.entra_google_domain_hint

        return f"{metadata.authorization_endpoint}?{urlencode(query)}"

    def complete_authorization(
        self,
        *,
        code: str,
        state: str,
        response: Response,
    ) -> str:
        self._ensure_configured()
        state_payload = read_auth_state_token(state)
        if state_payload is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid auth state",
            )

        metadata = self._fetch_metadata()
        tokens = self._exchange_code(code=code, token_endpoint=metadata.token_endpoint)
        claims = self._validate_id_token(
            id_token=tokens["id_token"],
            jwks_uri=metadata.jwks_uri,
            issuer=metadata.issuer,
            nonce=state_payload["nonce"],
        )
        identity = self._extract_identity(claims)
        user = self.auth_service.upsert_external_user(
            auth_provider_user_id=identity.provider_user_id,
            email=identity.email,
            name=identity.name,
        )
        self.auth_service.set_session_cookie(response=response, user_id=user.id)
        return state_payload["next"]

    def _ensure_configured(self) -> None:
        if settings.entra_external_id_enabled:
            return

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft Entra External ID is not configured",
        )

    def _fetch_metadata(self) -> OIDCMetadata:
        metadata_url = settings.entra_openid_configuration_url
        if metadata_url is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OIDC metadata URL is not configured",
            )

        with httpx.Client(timeout=10.0) as client:
            response = client.get(metadata_url)
            response.raise_for_status()
            payload = response.json()

        return OIDCMetadata(
            authorization_endpoint=payload["authorization_endpoint"],
            token_endpoint=payload["token_endpoint"],
            issuer=payload["issuer"],
            jwks_uri=payload["jwks_uri"],
        )

    def _exchange_code(self, *, code: str, token_endpoint: str) -> dict[str, str]:
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.entra_client_id or "",
            "client_secret": settings.entra_client_secret or "",
            "code": code,
            "redirect_uri": settings.entra_redirect_uri,
        }

        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.is_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not exchange the authorization code",
            )

        payload = response.json()
        id_token = payload.get("id_token")
        if not isinstance(id_token, str) or not id_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The identity provider did not return an ID token",
            )

        return {"id_token": id_token}

    def _validate_id_token(
        self,
        *,
        id_token: str,
        jwks_uri: str,
        issuer: str,
        nonce: str,
    ) -> dict[str, str]:
        jwk_client = jwt.PyJWKClient(jwks_uri)
        signing_key = jwk_client.get_signing_key_from_jwt(id_token)

        try:
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.entra_client_id,
                issuer=issuer,
                options={"require": ["exp", "iat", "sub", "nonce"]},
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The identity token could not be verified",
            ) from exc

        if claims.get("nonce") != nonce:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The identity token nonce is invalid",
            )

        return claims

    def _extract_identity(self, claims: dict[str, str]) -> ExternalIdentity:
        subject = claims.get("sub")
        email = claims.get("email") or claims.get("preferred_username")
        name = claims.get("name") or email

        if not isinstance(subject, str) or not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The identity token does not include a subject",
            )

        if not isinstance(email, str) or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The identity token does not include an email",
            )

        if not isinstance(name, str) or not name:
            name = email

        issuer_host = urlparse(claims.get("iss", "")).hostname or "entra"
        return ExternalIdentity(
            provider_user_id=f"{issuer_host}:{subject}",
            email=email,
            name=name,
        )

    def _sanitize_next_path(self, next_path: str) -> str:
        if not next_path.startswith("/") or next_path.startswith("//"):
            return "/app"

        return next_path

    def build_frontend_redirect_url(self, *, next_path: str, error: str | None = None) -> str:
        target = urljoin(settings.default_frontend_origin, self._sanitize_next_path(next_path))
        if error is None:
            return target

        login_url = urljoin(settings.default_frontend_origin, "/login")
        query = urlencode({"error": error, "next": next_path})
        return f"{login_url}?{query}"
