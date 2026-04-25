from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AssetType, enum_values
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.trade import Trade
    from app.models.user import User


class Holding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "holdings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_symbol: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(
            AssetType,
            name="asset_type",
            native_enum=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    weekly_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    monthly_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    recurring_last_applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    average_buy_price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    user: Mapped["User"] = relationship(back_populates="holdings")
    trades: Mapped[list["Trade"]] = relationship(back_populates="holding")
