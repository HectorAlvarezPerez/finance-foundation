from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PriceSource, enum_values
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Price(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prices"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "asset_symbol",
            "source",
            "as_of",
            name="uq_prices_user_symbol_source_as_of",
        ),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    asset_symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[PriceSource] = mapped_column(
        Enum(
            PriceSource,
            name="price_source",
            native_enum=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    user: Mapped["User | None"] = relationship(back_populates="prices")
