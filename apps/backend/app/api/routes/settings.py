from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUserId, DBSession
from app.repositories.settings_repository import SettingsRepository
from app.schemas.settings import SettingsRead, SettingsUpdate
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


def get_settings_service(db: DBSession) -> SettingsService:
    return SettingsService(SettingsRepository(db), db)


SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]


@router.get("", response_model=SettingsRead)
def get_settings(
    user_id: CurrentUserId,
    service: SettingsServiceDep,
) -> SettingsRead:
    settings = service.get_settings(user_id=user_id)
    return SettingsRead.model_validate(settings)


@router.put("", response_model=SettingsRead)
def upsert_settings(
    payload: SettingsUpdate,
    user_id: CurrentUserId,
    service: SettingsServiceDep,
) -> SettingsRead:
    settings = service.upsert_settings(user_id=user_id, payload=payload)
    return SettingsRead.model_validate(settings)
