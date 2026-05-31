import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import RuleMatchType
from app.schemas.common import ORMBaseModel


class CategorizationRuleCreate(BaseModel):
    category_id: uuid.UUID
    match_type: RuleMatchType = RuleMatchType.CONTAINS
    pattern: str = Field(min_length=1, max_length=255)
    priority: int = Field(default=0, ge=0, le=1000)


class CategorizationRuleRead(ORMBaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    match_type: RuleMatchType
    pattern: str
    priority: int
    created_at: datetime
    updated_at: datetime


class CategorizationRuleListResponse(BaseModel):
    items: list[CategorizationRuleRead]
    total: int
