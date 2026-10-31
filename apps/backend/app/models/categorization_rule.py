from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import RuleMatchType, enum_values
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CategorizationRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categorization_rules"

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
    match_type: Mapped[RuleMatchType] = mapped_column(
        Enum(
            RuleMatchType,
            name="rule_match_type",
            native_enum=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    pattern: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
