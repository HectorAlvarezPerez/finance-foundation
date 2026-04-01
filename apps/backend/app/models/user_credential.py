from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserCredential(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_credentials"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["User"] = relationship(back_populates="credential")
