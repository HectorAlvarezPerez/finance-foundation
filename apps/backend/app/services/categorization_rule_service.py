import uuid
from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.categorization_rule import CategorizationRule
from app.models.enums import RuleMatchType
from app.repositories.categorization_rule_repository import CategorizationRuleRepository
from app.repositories.category_repository import CategoryRepository
from app.schemas.categorization_rules import (
    CategorizationRuleCreate,
    CategorizationRuleListResponse,
    CategorizationRuleRead,
)


def match_rule_category(
    rules: Iterable[CategorizationRule], description: str
) -> uuid.UUID | None:
    """Return the category of the first rule (by priority) matching the description."""
    text = (description or "").casefold()
    for rule in rules:
        pattern = rule.pattern.casefold()
        if not pattern:
            continue
        if rule.match_type == RuleMatchType.CONTAINS and pattern in text:
            return rule.category_id
        if rule.match_type == RuleMatchType.EQUALS and pattern == text:
            return rule.category_id
        if rule.match_type == RuleMatchType.STARTS_WITH and text.startswith(pattern):
            return rule.category_id
    return None


class CategorizationRuleService:
    def __init__(
        self,
        repository: CategorizationRuleRepository,
        category_repository: CategoryRepository,
        db: Session,
    ) -> None:
        self.repository = repository
        self.category_repository = category_repository
        self.db = db

    def list_rules(self, *, user_id: uuid.UUID) -> CategorizationRuleListResponse:
        items = self.repository.list_for_user(user_id=user_id)
        return CategorizationRuleListResponse(
            items=[CategorizationRuleRead.model_validate(item) for item in items],
            total=len(items),
        )

    def create_rule(
        self, *, user_id: uuid.UUID, payload: CategorizationRuleCreate
    ) -> CategorizationRule:
        category = self.category_repository.get_for_user(
            user_id=user_id, category_id=payload.category_id
        )
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected category does not exist for the current user",
            )
        rule = self.repository.create(user_id=user_id, payload=payload.model_dump())
        self.db.commit()
        return rule

    def delete_rule(self, *, user_id: uuid.UUID, rule_id: uuid.UUID) -> None:
        rule = self.repository.get_for_user(user_id=user_id, rule_id=rule_id)
        if rule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found"
            )
        self.repository.delete(rule)
        self.db.commit()
