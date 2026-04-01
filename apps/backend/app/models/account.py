from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AccountType, enum_values
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.user import User


class Account(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[AccountType] = mapped_column(
        Enum(
            AccountType,
            name="account_type",
            native_enum=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    user: Mapped["User"] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")
