import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel


class SettingsUpdate(BaseModel):
    default_currency: str = Field(min_length=3, max_length=3)
    locale: str = Field(min_length=2, max_length=16)
    theme: str = Field(min_length=1, max_length=32)
    auto_categorization_enabled: bool = True


class SettingsRead(ORMBaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    default_currency: str
    locale: str
    theme: str
    auto_categorization_enabled: bool
    created_at: datetime
    updated_at: datetime
