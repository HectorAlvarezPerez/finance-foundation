import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_credential import UserCredential


class UserCredentialRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_user(self, *, user_id: uuid.UUID) -> UserCredential | None:
        statement = select(UserCredential).where(UserCredential.user_id == user_id)
        return self.db.scalar(statement)

    def create(self, *, user_id: uuid.UUID, password_hash: str) -> UserCredential:
        credential = UserCredential(user_id=user_id, password_hash=password_hash)
        self.db.add(credential)
        self.db.flush()
        self.db.refresh(credential)
        return credential
