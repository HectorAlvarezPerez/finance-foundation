import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import CurrentUserId, DBSession
from app.repositories.account_repository import AccountRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.accounts import AccountCreate, AccountListResponse, AccountRead, AccountUpdate
from app.services.account_service import AccountService

router = APIRouter(prefix="/accounts", tags=["accounts"])


def get_account_service(db: DBSession) -> AccountService:
    return AccountService(AccountRepository(db), TransactionRepository(db), db)


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]


@router.get("", response_model=AccountListResponse)
def list_accounts(
    user_id: CurrentUserId,
    service: AccountServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: Literal["created_at", "name"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> AccountListResponse:
    return service.list_accounts(
        user_id=user_id,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    user_id: CurrentUserId,
    service: AccountServiceDep,
) -> AccountRead:
    account = service.create_account(user_id=user_id, payload=payload)
    return AccountRead.model_validate(account)


@router.get("/{account_id}", response_model=AccountRead)
def get_account(
    account_id: uuid.UUID,
    user_id: CurrentUserId,
    service: AccountServiceDep,
) -> AccountRead:
    account = service.get_account(user_id=user_id, account_id=account_id)
    return AccountRead.model_validate(account)


@router.patch("/{account_id}", response_model=AccountRead)
def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    user_id: CurrentUserId,
    service: AccountServiceDep,
) -> AccountRead:
    account = service.update_account(user_id=user_id, account_id=account_id, payload=payload)
    return AccountRead.model_validate(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: uuid.UUID,
    user_id: CurrentUserId,
    service: AccountServiceDep,
) -> Response:
    service.delete_account(user_id=user_id, account_id=account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
