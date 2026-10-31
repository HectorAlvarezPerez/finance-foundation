import uuid

from fastapi import HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_session_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_credential_repository import UserCredentialRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthLoginRequest, AuthRegisterRequest


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        credential_repository: UserCredentialRepository,
        db: Session,
    ) -> None:
        self.user_repository = user_repository
        self.credential_repository = credential_repository
        self.db = db

    def register(self, *, payload: AuthRegisterRequest, response: Response) -> User:
        existing_user = self.user_repository.get_by_email(email=payload.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )

        user = self.user_repository.create(email=payload.email, name=payload.name)
        self.credential_repository.create(
            user_id=user.id,
            password_hash=hash_password(payload.password),
        )
        self.db.commit()
        self.set_session_cookie(response=response, user_id=user.id)
        return user

    def login(self, *, payload: AuthLoginRequest, response: Response) -> User:
        user = self.user_repository.get_by_email(email=payload.email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        credential = self.credential_repository.get_for_user(user_id=user.id)
        if credential is None or not verify_password(payload.password, credential.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        self.set_session_cookie(response=response, user_id=user.id)
        return user

    def logout(self, *, response: Response) -> None:
        response.delete_cookie(
            key=settings.session_cookie_name,
            path="/",
            httponly=True,
            samesite=settings.session_cookie_samesite,
            secure=settings.session_cookie_secure,
        )

    def get_user(self, *, user_id: uuid.UUID) -> User:
        user = self.user_repository.get(user_id=user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    def delete_account(self, *, user_id: uuid.UUID, response: Response) -> None:
        user = self.get_user(user_id=user_id)
        self.user_repository.delete(user=user)
        self.db.commit()
        self.logout(response=response)

    def upsert_external_user(
        self,
        *,
        auth_provider_user_id: str,
        email: str,
        name: str,
    ) -> User:
        user = self.user_repository.get_by_auth_provider_user_id(
            auth_provider_user_id=auth_provider_user_id
        )

        if user is None:
            user = self.user_repository.get_by_email(email=email)

        if user is None:
            user = self.user_repository.create(
                email=email,
                name=name,
                auth_provider_user_id=auth_provider_user_id,
            )
        else:
            user = self.user_repository.update_identity(
                user=user,
                email=email,
                name=name,
                auth_provider_user_id=auth_provider_user_id,
            )

        self.db.commit()
        return user

    def set_session_cookie(self, *, response: Response, user_id: uuid.UUID) -> None:
        response.set_cookie(
            key=settings.session_cookie_name,
            value=create_session_token(user_id),
            max_age=settings.session_cookie_max_age,
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite=settings.session_cookie_samesite,
            path="/",
        )
