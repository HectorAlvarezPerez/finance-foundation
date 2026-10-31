import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate
from app.repositories.exchange_rate_repository import ExchangeRateRepository
from app.schemas.exchange_rates import (
    ExchangeRateCreate,
    ExchangeRateListResponse,
    ExchangeRateRead,
)


class CurrencyConverter:
    """Converts amounts between currencies using a snapshot of latest rates.

    A rate (from, to) means 1 unit of ``from`` equals ``rate`` units of ``to``.
    Falls back to the inverse rate when only the opposite pair is known.
    Returns ``None`` when no conversion path exists.
    """

    def __init__(self, rates: dict[tuple[str, str], Decimal]) -> None:
        self._rates = rates

    def convert(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal | None:
        if from_currency == to_currency:
            return amount
        direct = self._rates.get((from_currency, to_currency))
        if direct is not None:
            return amount * direct
        inverse = self._rates.get((to_currency, from_currency))
        if inverse is not None and inverse != 0:
            return amount / inverse
        return None


class FxService:
    def __init__(self, repository: ExchangeRateRepository, db: Session) -> None:
        self.repository = repository
        self.db = db

    def list_rates(self, *, user_id: uuid.UUID) -> ExchangeRateListResponse:
        items = self.repository.list_for_user(user_id=user_id)
        return ExchangeRateListResponse(
            items=[ExchangeRateRead.model_validate(item) for item in items],
            total=len(items),
        )

    def create_rate(self, *, user_id: uuid.UUID, payload: ExchangeRateCreate) -> ExchangeRate:
        from_currency = payload.from_currency.upper()
        to_currency = payload.to_currency.upper()
        if from_currency == to_currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Las divisas de origen y destino deben ser distintas",
            )
        return self._create(
            user_id=user_id,
            from_currency=from_currency,
            to_currency=to_currency,
            rate=payload.rate,
        )

    def delete_rate(self, *, user_id: uuid.UUID, rate_id: uuid.UUID) -> None:
        rate = self.repository.get_for_user(user_id=user_id, rate_id=rate_id)
        if rate is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Exchange rate not found"
            )
        self.repository.delete(rate)
        self.db.commit()

    def build_converter(self, *, user_id: uuid.UUID) -> CurrencyConverter:
        return CurrencyConverter(self.repository.latest_rates_for_user(user_id=user_id))

    def _create(
        self,
        *,
        user_id: uuid.UUID,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
    ) -> ExchangeRate:
        created = self.repository.create(
            user_id=user_id,
            payload={
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": rate,
                "as_of": datetime.now(UTC),
            },
        )
        self.db.commit()
        return created
