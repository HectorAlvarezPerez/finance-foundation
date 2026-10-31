import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, *, user_id: uuid.UUID) -> User | None:
        statement = select(User).where(User.id == user_id)
        return self.db.scalar(statement)

    def get_by_email(self, *, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.db.scalar(statement)

    def get_by_auth_provider_user_id(self, *, auth_provider_user_id: str) -> User | None:
        statement = select(User).where(User.auth_provider_user_id == auth_provider_user_id)
        return self.db.scalar(statement)

    def create(
        self,
        *,
        email: str,
        name: str,
        auth_provider_user_id: str | None = None,
    ) -> User:
        user = User(
            auth_provider_user_id=auth_provider_user_id or f"local:{uuid.uuid4()}",
            email=email,
            name=name,
        )
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user

    def update_identity(
        self,
        *,
        user: User,
        email: str,
        name: str,
        auth_provider_user_id: str,
    ) -> User:
        user.email = email
        user.name = name
        user.auth_provider_user_id = auth_provider_user_id
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user

    def delete(self, *, user: User) -> None:
        self.db.delete(user)
