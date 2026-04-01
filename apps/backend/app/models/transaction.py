from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category
    from app.models.user import User


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="transactions")
    account: Mapped["Account"] = relationship(back_populates="transactions")
    category: Mapped["Category | None"] = relationship(back_populates="transactions")
