import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.settings import Settings


class SettingsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_user(self, *, user_id: uuid.UUID) -> Settings | None:
        statement = select(Settings).where(Settings.user_id == user_id)
        return self.db.scalar(statement)

    def create(self, *, user_id: uuid.UUID, payload: dict[str, object]) -> Settings:
        settings = Settings(user_id=user_id, **payload)
        self.db.add(settings)
        self.db.flush()
        self.db.refresh(settings)
        return settings

    def update(self, settings: Settings, *, payload: dict[str, object]) -> Settings:
        for field, value in payload.items():
            setattr(settings, field, value)

        self.db.add(settings)
        self.db.flush()
        self.db.refresh(settings)
        return settings
