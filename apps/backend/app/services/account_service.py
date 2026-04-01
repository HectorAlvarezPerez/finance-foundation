import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.account import Account
from app.repositories.account_repository import AccountRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.accounts import AccountCreate, AccountListResponse, AccountRead, AccountUpdate


class AccountService:
    def __init__(
        self,
        repository: AccountRepository,
        transaction_repository: TransactionRepository,
        db: Session,
    ) -> None:
        self.repository = repository
        self.transaction_repository = transaction_repository
        self.db = db

    def list_accounts(
        self,
        *,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> AccountListResponse:
        items, total = self.repository.list_for_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return AccountListResponse(
            items=[AccountRead.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_account(self, *, user_id: uuid.UUID, account_id: uuid.UUID) -> Account:
        account = self.repository.get_for_user(user_id=user_id, account_id=account_id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        return account

    def create_account(self, *, user_id: uuid.UUID, payload: AccountCreate) -> Account:
        initial_balance = payload.initial_balance
        account = self.repository.create(
            user_id=user_id,
            payload=payload.model_dump(exclude={"initial_balance"}),
        )

        if initial_balance != 0:
            self.transaction_repository.create(
                user_id=user_id,
                payload={
                    "account_id": account.id,
                    "category_id": None,
                    "date": date.today(),
                    "amount": initial_balance,
                    "currency": account.currency,
                    "description": "Saldo inicial",
                    "notes": "Transacción creada automáticamente al abrir la cuenta",
                },
            )

        self.db.commit()
        return account

    def update_account(
        self,
        *,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        payload: AccountUpdate,
    ) -> Account:
        account = self.get_account(user_id=user_id, account_id=account_id)
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return account
        account = self.repository.update(account, payload=updates)
        self.db.commit()
        return account

    def delete_account(self, *, user_id: uuid.UUID, account_id: uuid.UUID) -> None:
        account = self.get_account(user_id=user_id, account_id=account_id)
        try:
            self.transaction_repository.delete_for_account(user_id=user_id, account_id=account.id)
            self.repository.delete(account)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account cannot be deleted while it still has related transactions",
            ) from exc
