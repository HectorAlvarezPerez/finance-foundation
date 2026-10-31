import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import PriceSource
from app.models.price import Price


class PriceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def latest_prices_for_user(self, *, user_id: uuid.UUID) -> dict[str, Price]:
        """Latest price per asset_symbol for the user (most recent ``as_of`` wins)."""
        statement = (
            select(Price)
            .where(Price.user_id == user_id)
            .order_by(Price.asset_symbol.asc(), Price.as_of.desc())
        )
        latest: dict[str, Price] = {}
        for price in self.db.scalars(statement):
            latest.setdefault(price.asset_symbol, price)
        return latest

    def get_at(
        self,
        *,
        user_id: uuid.UUID,
        asset_symbol: str,
        source: PriceSource,
        as_of: datetime,
    ) -> Price | None:
        statement = select(Price).where(
            Price.user_id == user_id,
            Price.asset_symbol == asset_symbol,
            Price.source == source,
            Price.as_of == as_of,
        )
        return self.db.scalar(statement)

    def create(self, *, user_id: uuid.UUID, payload: dict[str, object]) -> Price:
        price = Price(user_id=user_id, **payload)
        self.db.add(price)
        self.db.flush()
        self.db.refresh(price)
        return price
