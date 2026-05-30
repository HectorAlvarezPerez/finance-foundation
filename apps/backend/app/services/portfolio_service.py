import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import PriceSource
from app.models.holding import Holding
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.schemas.portfolio import (
    HoldingCreate,
    HoldingListResponse,
    HoldingRead,
    HoldingUpdate,
    PortfolioHoldingRead,
    PortfolioSummaryRead,
)

ZERO = Decimal("0")


@dataclass
class _ComputedHolding:
    holding: Holding
    invested: Decimal
    current_price: Decimal | None
    current_value: Decimal | None
    unrealized_pnl: Decimal | None
    effective_value: Decimal


class PortfolioService:
    def __init__(
        self,
        holding_repository: HoldingRepository,
        price_repository: PriceRepository,
        db: Session,
    ) -> None:
        self.holding_repository = holding_repository
        self.price_repository = price_repository
        self.db = db

    def list_holdings(
        self,
        *,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> HoldingListResponse:
        items, total = self.holding_repository.list_for_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return HoldingListResponse(
            items=[HoldingRead.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_holding(self, *, user_id: uuid.UUID, holding_id: uuid.UUID) -> Holding:
        holding = self.holding_repository.get_for_user(user_id=user_id, holding_id=holding_id)
        if holding is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")
        return holding

    def create_holding(self, *, user_id: uuid.UUID, payload: HoldingCreate) -> Holding:
        data = payload.model_dump()
        # Recurring-contribution fields are not part of the MVP; default them.
        data.update(
            weekly_quantity=ZERO,
            monthly_quantity=ZERO,
            recurring_last_applied_at=datetime.now(UTC),
        )
        holding = self.holding_repository.create(user_id=user_id, payload=data)
        self.db.commit()
        return holding

    def update_holding(
        self,
        *,
        user_id: uuid.UUID,
        holding_id: uuid.UUID,
        payload: HoldingUpdate,
    ) -> Holding:
        holding = self.get_holding(user_id=user_id, holding_id=holding_id)
        updates = payload.model_dump(exclude_unset=True)
        if updates:
            holding = self.holding_repository.update(holding, payload=updates)
            self.db.commit()
        return holding

    def delete_holding(self, *, user_id: uuid.UUID, holding_id: uuid.UUID) -> None:
        holding = self.get_holding(user_id=user_id, holding_id=holding_id)
        self.holding_repository.delete(holding)
        self.db.commit()

    def update_price(
        self,
        *,
        user_id: uuid.UUID,
        holding_id: uuid.UUID,
        price: Decimal,
    ) -> Holding:
        holding = self.get_holding(user_id=user_id, holding_id=holding_id)
        if not holding.asset_symbol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El activo necesita un símbolo para registrar su precio actual",
            )
        self.price_repository.create(
            user_id=user_id,
            payload={
                "asset_symbol": holding.asset_symbol,
                "source": PriceSource.MANUAL,
                "price": price,
                "currency": holding.currency,
                "as_of": datetime.now(UTC),
            },
        )
        self.db.commit()
        return holding

    def get_summary(self, *, user_id: uuid.UUID) -> PortfolioSummaryRead:
        holdings = self.holding_repository.list_all_for_user(user_id=user_id)
        latest_prices = self.price_repository.latest_prices_for_user(user_id=user_id)

        computed: list[_ComputedHolding] = []
        total_value = ZERO
        total_invested = ZERO
        total_pnl = ZERO

        for holding in holdings:
            invested = (holding.quantity * holding.average_buy_price).quantize(Decimal("0.01"))
            price_row = latest_prices.get(holding.asset_symbol) if holding.asset_symbol else None
            current_price = price_row.price if price_row is not None else None

            if current_price is not None:
                current_value = (holding.quantity * current_price).quantize(Decimal("0.01"))
                unrealized_pnl = current_value - invested
            else:
                current_value = None
                unrealized_pnl = None

            effective_value = current_value if current_value is not None else invested
            total_value += effective_value
            total_invested += invested
            if unrealized_pnl is not None:
                total_pnl += unrealized_pnl

            computed.append(
                _ComputedHolding(
                    holding=holding,
                    invested=invested,
                    current_price=current_price,
                    current_value=current_value,
                    unrealized_pnl=unrealized_pnl,
                    effective_value=effective_value,
                )
            )

        holding_reads: list[PortfolioHoldingRead] = []
        for entry in computed:
            holding = entry.holding
            allocation = (
                float(entry.effective_value / total_value * 100) if total_value > 0 else 0.0
            )
            holding_reads.append(
                PortfolioHoldingRead(
                    id=holding.id,
                    asset_name=holding.asset_name,
                    asset_symbol=holding.asset_symbol,
                    asset_type=holding.asset_type,
                    quantity=holding.quantity,
                    average_buy_price=holding.average_buy_price,
                    currency=holding.currency,
                    invested=entry.invested,
                    current_price=entry.current_price,
                    current_value=entry.current_value,
                    unrealized_pnl=entry.unrealized_pnl,
                    allocation_pct=round(allocation, 2),
                )
            )

        return PortfolioSummaryRead(
            holdings=holding_reads,
            total_invested=total_invested,
            total_value=total_value,
            total_unrealized_pnl=total_pnl,
        )
