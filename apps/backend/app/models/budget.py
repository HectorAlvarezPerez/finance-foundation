from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.user import User


class Budget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "category_id",
            "year",
            "month",
            name="uq_budgets_user_category_year_month",
        ),
        CheckConstraint("month >= 1 AND month <= 12", name="budget_month_range"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    user: Mapped["User"] = relationship(back_populates="budgets")
    category: Mapped["Category"] = relationship(back_populates="budgets")
