import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.categorization_rule import CategorizationRule


class CategorizationRuleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, *, user_id: uuid.UUID) -> list[CategorizationRule]:
        statement = (
            select(CategorizationRule)
            .where(CategorizationRule.user_id == user_id)
            .order_by(CategorizationRule.priority.asc(), CategorizationRule.created_at.asc())
        )
        return list(self.db.scalars(statement))

    def get_for_user(self, *, user_id: uuid.UUID, rule_id: uuid.UUID) -> CategorizationRule | None:
        statement = select(CategorizationRule).where(
            CategorizationRule.user_id == user_id, CategorizationRule.id == rule_id
        )
        return self.db.scalar(statement)

    def create(self, *, user_id: uuid.UUID, payload: dict[str, object]) -> CategorizationRule:
        rule = CategorizationRule(user_id=user_id, **payload)
        self.db.add(rule)
        self.db.flush()
        self.db.refresh(rule)
        return rule

    def delete(self, rule: CategorizationRule) -> None:
        self.db.delete(rule)
        self.db.flush()
