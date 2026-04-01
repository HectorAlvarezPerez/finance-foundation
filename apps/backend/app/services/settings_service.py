import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.settings import Settings
from app.repositories.settings_repository import SettingsRepository
from app.schemas.settings import SettingsUpdate


class SettingsService:
    def __init__(self, repository: SettingsRepository, db: Session) -> None:
        self.repository = repository
        self.db = db

    def get_settings(self, *, user_id: uuid.UUID) -> Settings:
        settings = self.repository.get_for_user(user_id=user_id)
        if settings is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found")
        return settings

    def upsert_settings(self, *, user_id: uuid.UUID, payload: SettingsUpdate) -> Settings:
        existing = self.repository.get_for_user(user_id=user_id)
        if existing is None:
            settings = self.repository.create(user_id=user_id, payload=payload.model_dump())
        else:
            settings = self.repository.update(existing, payload=payload.model_dump())
        self.db.commit()
        return settings
