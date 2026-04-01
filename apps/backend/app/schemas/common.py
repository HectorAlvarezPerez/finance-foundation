from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedRead(ORMBaseModel):
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
