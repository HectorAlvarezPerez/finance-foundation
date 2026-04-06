import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException, Response, status

from app.core.config import settings
from app.core.security import create_auth_state_token, read_auth_state_token
from app.services.auth_redirects import build_frontend_redirect_url, sanitize_next_path
from app.services.auth_service import AuthService


@dataclass
class GoogleOIDCMetadata:
    authorization_endpoint: str
    token_endpoint: str
    issuer: str
    jwks_uri: str


@dataclass
class GoogleIdentity:
    provider_user_id: str
    email: str
    name: str


class GoogleAuthService:
    def __init__(self, auth_service: AuthService) -> None:
        self.auth_service = auth_service

    def build_authorization_url(self, *, next_path: str) -> str:
        self._ensure_configured()
        metadata = self._fetch_metadata()
        nonce = secrets.token_urlsafe(16)
        state = create_auth_state_token(
            {
                "next": sanitize_next_path(next_path),
                "nonce": nonce,
            }
        )
        query = {
            "client_id": settings.google_oauth_client_id or "",
            "redirect_uri": settings.google_oauth_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "prompt": "select_account",
        }
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
        if settings.google_oauth_enabled:
            return

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured",
        )

    def _fetch_metadata(self) -> GoogleOIDCMetadata:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(settings.google_oauth_metadata_url)
            response.raise_for_status()
            payload = response.json()

        return GoogleOIDCMetadata(
            authorization_endpoint=payload["authorization_endpoint"],
            token_endpoint=payload["token_endpoint"],
            issuer=payload["issuer"],
            jwks_uri=payload["jwks_uri"],
        )

    def _exchange_code(self, *, code: str, token_endpoint: str) -> dict[str, str]:
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.google_oauth_client_id or "",
            "client_secret": settings.google_oauth_client_secret or "",
            "code": code,
            "redirect_uri": settings.google_oauth_redirect_uri,
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
                detail="Could not exchange the Google authorization code",
            )

        payload = response.json()
        id_token = payload.get("id_token")
        if not isinstance(id_token, str) or not id_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google did not return an ID token",
            )

        return {"id_token": id_token}

    def _validate_id_token(
        self,
        *,
        id_token: str,
        jwks_uri: str,
        issuer: str,
        nonce: str,
    ) -> Mapping[str, object]:
        jwk_client = jwt.PyJWKClient(jwks_uri)
        signing_key = jwk_client.get_signing_key_from_jwt(id_token)

        try:
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.google_oauth_client_id,
                issuer=[issuer, "accounts.google.com"],
                options={"require": ["exp", "iat", "sub", "nonce"]},
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The Google identity token could not be verified",
            ) from exc

        if claims.get("nonce") != nonce:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The Google identity token nonce is invalid",
            )

        return claims

    def _extract_identity(self, claims: Mapping[str, object]) -> GoogleIdentity:
        subject = claims.get("sub")
        email = claims.get("email")
        name = claims.get("name") or email
        email_verified = claims.get("email_verified")

        if not isinstance(subject, str) or not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google did not include a subject",
            )

        if not isinstance(email, str) or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google did not include an email",
            )

        if email_verified is False:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google email is not verified",
            )

        return GoogleIdentity(
            provider_user_id=f"google:{subject}",
            email=email,
            name=name if isinstance(name, str) and name else email,
        )

    def build_frontend_redirect_url(self, *, next_path: str, error: str | None = None) -> str:
        return build_frontend_redirect_url(
            default_frontend_origin=settings.default_frontend_origin,
            next_path=next_path,
            error=error,
        )
