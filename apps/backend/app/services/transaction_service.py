import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.enums import CategoryType
from app.models.transaction import Transaction
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transactions import (
    TransactionCreate,
    TransactionListResponse,
    TransactionRead,
    TransactionUpdate,
)


class TransactionService:
    def __init__(
        self,
        repository: TransactionRepository,
        account_repository: AccountRepository,
        category_repository: CategoryRepository,
        db: Session,
    ) -> None:
        self.repository = repository
        self.account_repository = account_repository
        self.category_repository = category_repository
        self.db = db

    def list_transactions(
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
    ) -> TransactionListResponse:
        items, total = self.repository.list_for_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
            account_id=account_id,
            category_id=category_id,
            category_type=category_type,
            date_from=date_from,
            date_to=date_to,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return TransactionListResponse(
            items=[TransactionRead.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_transaction(self, *, user_id: uuid.UUID, transaction_id: uuid.UUID) -> Transaction:
        transaction = self.repository.get_for_user(user_id=user_id, transaction_id=transaction_id)
        if transaction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found",
            )
        return transaction

    def create_transaction(self, *, user_id: uuid.UUID, payload: TransactionCreate) -> Transaction:
        account = self._require_account(user_id=user_id, account_id=payload.account_id)
        category = self._require_category_if_present(
            user_id=user_id,
            category_id=payload.category_id,
        )
        self._validate_currency_matches_account(currency=payload.currency, account=account)
        self._validate_category_is_compatible(category=category)

        transaction = self.repository.create(user_id=user_id, payload=payload.model_dump())
        self.db.commit()
        return transaction

    def update_transaction(
        self,
        *,
        user_id: uuid.UUID,
        transaction_id: uuid.UUID,
        payload: TransactionUpdate,
    ) -> Transaction:
        transaction = self.get_transaction(user_id=user_id, transaction_id=transaction_id)
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return transaction

        account_id = updates.get("account_id", transaction.account_id)
        category_id = updates.get("category_id", transaction.category_id)
        currency = updates.get("currency", transaction.currency)

        account = self._require_account(user_id=user_id, account_id=account_id)
        category = self._require_category_if_present(user_id=user_id, category_id=category_id)
        self._validate_currency_matches_account(currency=currency, account=account)
        self._validate_category_is_compatible(category=category)

        transaction = self.repository.update(transaction, payload=updates)
        self.db.commit()
        return transaction

    def delete_transaction(self, *, user_id: uuid.UUID, transaction_id: uuid.UUID) -> None:
        transaction = self.get_transaction(user_id=user_id, transaction_id=transaction_id)
        self.repository.delete(transaction)
        self.db.commit()

    def _require_account(self, *, user_id: uuid.UUID, account_id: uuid.UUID) -> Account:
        account = self.account_repository.get_for_user(user_id=user_id, account_id=account_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected account does not exist for the current user",
            )
        return account

    def _require_category_if_present(
        self,
        *,
        user_id: uuid.UUID,
        category_id: uuid.UUID | None,
    ) -> Category | None:
        if category_id is None:
            return None

        category = self.category_repository.get_for_user(user_id=user_id, category_id=category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected category does not exist for the current user",
            )
        return category

    def _validate_currency_matches_account(self, *, currency: str, account: Account) -> None:
        if currency != account.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction currency must match the selected account currency",
            )

    def _validate_category_is_compatible(self, *, category: Category | None) -> None:
        if category is None:
            return
        # Transfer categories remain allowed in this v1 because the domain supports them.
        return
