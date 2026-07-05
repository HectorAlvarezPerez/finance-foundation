from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

import httpx
from sqlalchemy.orm import Session

from app.models.enums import AssetType, PriceSource
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository

CRYPTO_ASSET_TYPES = {AssetType.CRYPTO}
HTTP_TIMEOUT = 10.0


class PriceProvider(Protocol):
    def fetch_price(self, *, symbol: str, currency: str) -> Decimal | None: ...


class CoinGeckoProvider:
    """Free, keyless crypto prices. 1 call returns the price in the target currency."""

    BASE_URL = "https://api.coingecko.com/api/v3"

    def fetch_price(self, *, symbol: str, currency: str) -> Decimal | None:
        try:
            response = httpx.get(
                f"{self.BASE_URL}/coins/markets",
                params={"vs_currency": currency.lower(), "symbols": symbol.lower()},
                timeout=HTTP_TIMEOUT,
            )
            response.raise_for_status()
            rows = response.json()
        except (httpx.HTTPError, ValueError):
            return None

        if not isinstance(rows, list) or not rows:
            return None
        price = rows[0].get("current_price")
        return _to_decimal(price)


class TwelveDataProvider:
    """Stocks/ETFs prices. Requires an API key (free tier available)."""

    BASE_URL = "https://api.twelvedata.com"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def fetch_price(self, *, symbol: str, currency: str) -> Decimal | None:
        # /price returns the US-listing price in USD; convert when the holding
        # is denominated in another currency. Better no price than a wrong one.
        price_usd = self._fetch_quote(symbol)
        if price_usd is None:
            return None

        target = currency.upper()
        if target == "USD":
            return price_usd

        rate = self._fetch_quote(f"USD/{target}")
        if rate is None:
            return None
        return price_usd * rate

    def _fetch_quote(self, symbol: str) -> Decimal | None:
        try:
            response = httpx.get(
                f"{self.BASE_URL}/price",
                params={"symbol": symbol, "apikey": self.api_key},
                timeout=HTTP_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return None

        if not isinstance(payload, dict):
            return None
        return _to_decimal(payload.get("price"))


def _to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result > 0 else None


@dataclass
class PriceRefreshResult:
    updated: list[dict[str, str]] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)


class PriceFetchService:
    def __init__(
        self,
        holding_repository: HoldingRepository,
        price_repository: PriceRepository,
        db: Session,
        *,
        crypto_provider: PriceProvider,
        stock_provider: PriceProvider | None,
    ) -> None:
        self.holding_repository = holding_repository
        self.price_repository = price_repository
        self.db = db
        self.crypto_provider = crypto_provider
        self.stock_provider = stock_provider

    def refresh_prices(self, *, user_id: uuid.UUID) -> PriceRefreshResult:
        result = PriceRefreshResult()
        holdings = self.holding_repository.list_all_for_user(user_id=user_id)
        now = datetime.now(UTC)

        for holding in holdings:
            symbol = holding.asset_symbol
            if not symbol:
                result.failed.append({"asset": holding.asset_name, "reason": "sin símbolo"})
                continue

            is_crypto = holding.asset_type in CRYPTO_ASSET_TYPES
            provider = self.crypto_provider if is_crypto else self.stock_provider
            if provider is None:
                result.failed.append(
                    {"asset": symbol, "reason": "proveedor de bolsa no configurado"}
                )
                continue

            price = provider.fetch_price(symbol=symbol, currency=holding.currency)
            if price is None:
                result.failed.append({"asset": symbol, "reason": "precio no disponible"})
                continue

            self.price_repository.create(
                user_id=user_id,
                payload={
                    "asset_symbol": symbol,
                    "source": PriceSource.API,
                    "price": price,
                    "currency": holding.currency,
                    "as_of": now,
                },
            )
            result.updated.append({"asset": symbol, "price": str(price)})

        self.db.commit()
        return result
