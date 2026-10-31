import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import CurrentUserId, DBSession
from app.repositories.categorization_rule_repository import CategorizationRuleRepository
from app.repositories.category_repository import CategoryRepository
from app.schemas.categorization_rules import (
    CategorizationRuleCreate,
    CategorizationRuleListResponse,
    CategorizationRuleRead,
)
from app.services.categorization_rule_service import CategorizationRuleService

router = APIRouter(prefix="/categorization-rules", tags=["categorization-rules"])


def get_rule_service(db: DBSession) -> CategorizationRuleService:
    return CategorizationRuleService(
        CategorizationRuleRepository(db), CategoryRepository(db), db
    )


RuleServiceDep = Annotated[CategorizationRuleService, Depends(get_rule_service)]


@router.get("", response_model=CategorizationRuleListResponse)
def list_rules(user_id: CurrentUserId, service: RuleServiceDep) -> CategorizationRuleListResponse:
    return service.list_rules(user_id=user_id)


@router.post("", response_model=CategorizationRuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: CategorizationRuleCreate,
    user_id: CurrentUserId,
    service: RuleServiceDep,
) -> CategorizationRuleRead:
    rule = service.create_rule(user_id=user_id, payload=payload)
    return CategorizationRuleRead.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: uuid.UUID,
    user_id: CurrentUserId,
    service: RuleServiceDep,
) -> Response:
    service.delete_rule(user_id=user_id, rule_id=rule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
