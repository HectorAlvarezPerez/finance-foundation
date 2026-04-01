import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import CurrentUserId, DBSession
from app.models.enums import CategoryType
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transactions import (
    TransactionCreate,
    TransactionListResponse,
    TransactionRead,
    TransactionUpdate,
)
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


def get_transaction_service(db: DBSession) -> TransactionService:
    return TransactionService(
        TransactionRepository(db),
        AccountRepository(db),
        CategoryRepository(db),
        db,
    )


TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    user_id: CurrentUserId,
    service: TransactionServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    category_type: CategoryType | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = Query(default=None, min_length=1, max_length=255),
    sort_by: Literal["amount", "created_at", "date"] = "date",
    sort_order: Literal["asc", "desc"] = "desc",
) -> TransactionListResponse:
    return service.list_transactions(
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


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    user_id: CurrentUserId,
    service: TransactionServiceDep,
) -> TransactionRead:
    transaction = service.create_transaction(user_id=user_id, payload=payload)
    return TransactionRead.model_validate(transaction)


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(
    transaction_id: uuid.UUID,
    user_id: CurrentUserId,
    service: TransactionServiceDep,
) -> TransactionRead:
    transaction = service.get_transaction(user_id=user_id, transaction_id=transaction_id)
    return TransactionRead.model_validate(transaction)


@router.patch("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    user_id: CurrentUserId,
    service: TransactionServiceDep,
) -> TransactionRead:
    transaction = service.update_transaction(
        user_id=user_id,
        transaction_id=transaction_id,
        payload=payload,
    )
    return TransactionRead.model_validate(transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: uuid.UUID,
    user_id: CurrentUserId,
    service: TransactionServiceDep,
) -> Response:
    service.delete_transaction(user_id=user_id, transaction_id=transaction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
