import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate


class ExchangeRateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, *, user_id: uuid.UUID) -> list[ExchangeRate]:
        statement = (
            select(ExchangeRate)
            .where(ExchangeRate.user_id == user_id)
            .order_by(
                ExchangeRate.from_currency.asc(),
                ExchangeRate.to_currency.asc(),
                ExchangeRate.as_of.desc(),
            )
        )
        return list(self.db.scalars(statement))

    def latest_rates_for_user(self, *, user_id: uuid.UUID) -> dict[tuple[str, str], Decimal]:
        """Latest rate per (from_currency, to_currency) pair for the user."""
        statement = (
            select(ExchangeRate)
            .where(ExchangeRate.user_id == user_id)
            .order_by(ExchangeRate.as_of.desc())
        )
        latest: dict[tuple[str, str], Decimal] = {}
        for rate in self.db.scalars(statement):
            latest.setdefault((rate.from_currency, rate.to_currency), rate.rate)
        return latest

    def get_for_user(self, *, user_id: uuid.UUID, rate_id: uuid.UUID) -> ExchangeRate | None:
        statement = select(ExchangeRate).where(
            ExchangeRate.user_id == user_id, ExchangeRate.id == rate_id
        )
        return self.db.scalar(statement)

    def create(self, *, user_id: uuid.UUID, payload: dict[str, object]) -> ExchangeRate:
        rate = ExchangeRate(user_id=user_id, **payload)
        self.db.add(rate)
        self.db.flush()
        self.db.refresh(rate)
        return rate

    def delete(self, rate: ExchangeRate) -> None:
        self.db.delete(rate)
        self.db.flush()
