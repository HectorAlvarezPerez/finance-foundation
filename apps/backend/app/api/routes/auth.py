from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse

from app.api.deps import CurrentUserId, DBSession
from app.core.config import settings
from app.repositories.user_credential_repository import UserCredentialRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthLoginRequest, AuthProvidersRead, AuthRegisterRequest, AuthUserRead
from app.services.auth_service import AuthService
from app.services.entra_auth_service import EntraAuthService
from app.services.google_auth_service import GoogleAuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: DBSession) -> AuthService:
    return AuthService(UserRepository(db), UserCredentialRepository(db), db)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_entra_auth_service(service: AuthServiceDep) -> EntraAuthService:
    return EntraAuthService(service)


def get_google_auth_service(service: AuthServiceDep) -> GoogleAuthService:
    return GoogleAuthService(service)


EntraAuthServiceDep = Annotated[EntraAuthService, Depends(get_entra_auth_service)]
GoogleAuthServiceDep = Annotated[GoogleAuthService, Depends(get_google_auth_service)]


@router.post("/register", response_model=AuthUserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: AuthRegisterRequest,
    response: Response,
    service: AuthServiceDep,
) -> AuthUserRead:
    user = service.register(payload=payload, response=response)
    return AuthUserRead.model_validate(user)


@router.post("/login", response_model=AuthUserRead)
def login(
    payload: AuthLoginRequest,
    response: Response,
    service: AuthServiceDep,
) -> AuthUserRead:
    user = service.login(payload=payload, response=response)
    return AuthUserRead.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(service: AuthServiceDep) -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    service.logout(response=response)
    return response


@router.get("/me", response_model=AuthUserRead)
def me(user_id: CurrentUserId, service: AuthServiceDep) -> AuthUserRead:
    user = service.get_user(user_id=user_id)
    return AuthUserRead.model_validate(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(user_id: CurrentUserId, service: AuthServiceDep) -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    service.delete_account(user_id=user_id, response=response)
    return response


@router.get("/providers", response_model=AuthProvidersRead)
def providers(
    *,
    service: EntraAuthServiceDep,
) -> AuthProvidersRead:
    availability = service.get_provider_availability()
    availability["google_enabled"] = settings.google_oauth_enabled
    return AuthProvidersRead.model_validate(availability)


@router.get("/entra/start", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
def start_entra_login(
    *,
    service: EntraAuthServiceDep,
    next_path: str = Query(default="/app", alias="next"),
) -> RedirectResponse:
    authorization_url = service.build_authorization_url(next_path=next_path)
    return RedirectResponse(url=authorization_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/google/start", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
def start_google_login(
    *,
    service: GoogleAuthServiceDep,
    next_path: str = Query(default="/app", alias="next"),
) -> RedirectResponse:
    authorization_url = service.build_authorization_url(next_path=next_path)
    return RedirectResponse(url=authorization_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/google/callback", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
def complete_google_login(
    *,
    service: GoogleAuthServiceDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    if error is not None:
        target = service.build_frontend_redirect_url(
            next_path="/app",
            error=error_description or error,
        )
        return RedirectResponse(url=target, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    if code is None or state is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code or state",
        )

    response = RedirectResponse(url="/app", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    next_path = service.complete_authorization(code=code, state=state, response=response)
    response.headers["location"] = service.build_frontend_redirect_url(next_path=next_path)
    return response


@router.get("/entra/callback", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
def complete_entra_login(
    *,
    service: EntraAuthServiceDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    if error is not None:
        target = service.build_frontend_redirect_url(
            next_path="/app",
            error=error_description or error,
        )
        return RedirectResponse(url=target, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    if code is None or state is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code or state",
        )

    response = RedirectResponse(url="/app", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    next_path = service.complete_authorization(code=code, state=state, response=response)
    response.headers["location"] = service.build_frontend_redirect_url(next_path=next_path)
    return response
