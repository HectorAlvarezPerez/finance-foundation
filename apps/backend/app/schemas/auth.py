import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMBaseModel


class AuthRegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthUserRead(ORMBaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: datetime


class AuthProvidersRead(BaseModel):
    local_password_enabled: bool
    entra_external_id_enabled: bool
    google_enabled: bool
