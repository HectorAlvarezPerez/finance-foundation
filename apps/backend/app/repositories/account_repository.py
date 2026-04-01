import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.account import Account


class AccountRepository:
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
    ) -> tuple[list[Account], int]:
        statement: Select[tuple[Account]] = select(Account).where(Account.user_id == user_id)
        count_statement = (
            select(func.count()).select_from(Account).where(Account.user_id == user_id)
        )

        sort_column = Account.name if sort_by == "name" else Account.created_at
        statement = statement.order_by(
            sort_column.asc() if sort_order == "asc" else sort_column.desc()
        )
        statement = statement.limit(limit).offset(offset)

        items = list(self.db.scalars(statement))
        total = self.db.scalar(count_statement) or 0
        return items, total

    def list_all_for_user(
        self,
        *,
        user_id: uuid.UUID,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[Account]:
        statement: Select[tuple[Account]] = select(Account).where(Account.user_id == user_id)
        sort_column = Account.name if sort_by == "name" else Account.created_at
        statement = statement.order_by(
            sort_column.asc() if sort_order == "asc" else sort_column.desc()
        )
        return list(self.db.scalars(statement))

    def get_for_user(self, *, user_id: uuid.UUID, account_id: uuid.UUID) -> Account | None:
        statement = select(Account).where(Account.user_id == user_id, Account.id == account_id)
        return self.db.scalar(statement)

    def create(self, *, user_id: uuid.UUID, payload: dict[str, object]) -> Account:
        account = Account(user_id=user_id, **payload)
        self.db.add(account)
        self.db.flush()
        self.db.refresh(account)
        return account

    def update(self, account: Account, *, payload: dict[str, object]) -> Account:
        for field, value in payload.items():
            setattr(account, field, value)

        self.db.add(account)
        self.db.flush()
        self.db.refresh(account)
        return account

    def delete(self, account: Account) -> None:
        self.db.delete(account)
        self.db.flush()
