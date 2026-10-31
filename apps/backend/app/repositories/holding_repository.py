import uuid

from sqlalchemy import Select, func, select
from sqlalchemy import delete as sa_delete
from sqlalchemy.orm import Session

from app.models.holding import Holding

SORT_MAP = {
    "asset_name": Holding.asset_name,
    "created_at": Holding.created_at,
}


class HoldingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Holding], int]:
        statement: Select[tuple[Holding]] = select(Holding).where(Holding.user_id == user_id)
        count_statement = (
            select(func.count()).select_from(Holding).where(Holding.user_id == user_id)
        )

        sort_column = SORT_MAP.get(sort_by, Holding.created_at)
        statement = statement.order_by(
            sort_column.asc() if sort_order == "asc" else sort_column.desc()
        )
        statement = statement.limit(limit).offset(offset)

        items = list(self.db.scalars(statement))
        total = self.db.scalar(count_statement) or 0
        return items, total

    def list_all_for_user(self, *, user_id: uuid.UUID) -> list[Holding]:
        statement = (
            select(Holding).where(Holding.user_id == user_id).order_by(Holding.created_at.asc())
        )
        return list(self.db.scalars(statement))

    def get_for_user(self, *, user_id: uuid.UUID, holding_id: uuid.UUID) -> Holding | None:
        statement = select(Holding).where(
            Holding.user_id == user_id, Holding.id == holding_id
        )
        return self.db.scalar(statement)

    def create(self, *, user_id: uuid.UUID, payload: dict[str, object]) -> Holding:
        holding = Holding(user_id=user_id, **payload)
        self.db.add(holding)
        self.db.flush()
        self.db.refresh(holding)
        return holding

    def update(self, holding: Holding, *, payload: dict[str, object]) -> Holding:
        for field, value in payload.items():
            setattr(holding, field, value)
        self.db.add(holding)
        self.db.flush()
        self.db.refresh(holding)
        return holding

    def delete(self, holding: Holding) -> None:
        self.db.delete(holding)
        self.db.flush()

    def delete_all_for_user(self, *, user_id: uuid.UUID) -> None:
        self.db.execute(sa_delete(Holding).where(Holding.user_id == user_id))
        self.db.flush()
