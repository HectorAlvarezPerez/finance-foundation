import uuid
from datetime import date

from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import CategoryType
from app.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
        account_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        category_type: CategoryType | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        sort_by: str = "date",
        sort_order: str = "desc",
    ) -> tuple[list[Transaction], int]:
        statement: Select[tuple[Transaction]] = select(Transaction).where(
            Transaction.user_id == user_id
        )
        count_statement = (
            select(func.count()).select_from(Transaction).where(Transaction.user_id == user_id)
        )

        if category_type is not None:
            statement = statement.join(Category, Transaction.category_id == Category.id).where(
                Category.type == category_type
            )
            count_statement = count_statement.join(
                Category, Transaction.category_id == Category.id
            ).where(Category.type == category_type)

        if account_id is not None:
            statement = statement.where(Transaction.account_id == account_id)
            count_statement = count_statement.where(Transaction.account_id == account_id)

        if category_id is not None:
            statement = statement.where(Transaction.category_id == category_id)
            count_statement = count_statement.where(Transaction.category_id == category_id)

        if date_from is not None:
            statement = statement.where(Transaction.date >= date_from)
            count_statement = count_statement.where(Transaction.date >= date_from)

        if date_to is not None:
            statement = statement.where(Transaction.date <= date_to)
            count_statement = count_statement.where(Transaction.date <= date_to)

        if search:
            pattern = f"%{search}%"
            search_filter = or_(
                Transaction.description.ilike(pattern),
                Transaction.notes.ilike(pattern),
            )
            statement = statement.where(search_filter)
            count_statement = count_statement.where(search_filter)

        sort_map = {
            "amount": Transaction.amount,
            "created_at": Transaction.created_at,
            "date": Transaction.date,
        }
        sort_column = sort_map.get(sort_by, Transaction.date)
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
        account_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        category_type: CategoryType | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        sort_by: str = "date",
        sort_order: str = "desc",
    ) -> list[Transaction]:
        statement: Select[tuple[Transaction]] = select(Transaction).where(
            Transaction.user_id == user_id
        )

        if category_type is not None:
            statement = statement.join(Category, Transaction.category_id == Category.id).where(
                Category.type == category_type
            )

        if account_id is not None:
            statement = statement.where(Transaction.account_id == account_id)

        if category_id is not None:
            statement = statement.where(Transaction.category_id == category_id)

        if date_from is not None:
            statement = statement.where(Transaction.date >= date_from)

        if date_to is not None:
            statement = statement.where(Transaction.date <= date_to)

        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(
                    Transaction.description.ilike(pattern),
                    Transaction.notes.ilike(pattern),
                )
            )

        sort_map = {
            "amount": Transaction.amount,
            "created_at": Transaction.created_at,
            "date": Transaction.date,
        }
        sort_column = sort_map.get(sort_by, Transaction.date)
        statement = statement.order_by(
            sort_column.asc() if sort_order == "asc" else sort_column.desc()
        )

        return list(self.db.scalars(statement))

    def get_for_user(self, *, user_id: uuid.UUID, transaction_id: uuid.UUID) -> Transaction | None:
        statement = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.id == transaction_id,
        )
        return self.db.scalar(statement)

    def create(self, *, user_id: uuid.UUID, payload: dict[str, object]) -> Transaction:
        transaction = Transaction(user_id=user_id, **payload)
        self.db.add(transaction)
        self.db.flush()
        self.db.refresh(transaction)
        return transaction

    def update(self, transaction: Transaction, *, payload: dict[str, object]) -> Transaction:
        for field, value in payload.items():
            setattr(transaction, field, value)

        self.db.add(transaction)
        self.db.flush()
        self.db.refresh(transaction)
        return transaction

    def delete(self, transaction: Transaction) -> None:
        self.db.delete(transaction)
        self.db.flush()

    def delete_for_account(self, *, user_id: uuid.UUID, account_id: uuid.UUID) -> None:
        statement = delete(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.account_id == account_id,
        )
        self.db.execute(statement)
        self.db.flush()
