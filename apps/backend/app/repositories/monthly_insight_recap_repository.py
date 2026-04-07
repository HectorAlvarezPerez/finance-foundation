import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.monthly_insight_recap import MonthlyInsightRecap


class MonthlyInsightRecapRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_user_and_month(
        self,
        *,
        user_id: uuid.UUID,
        month_key: str,
    ) -> MonthlyInsightRecap | None:
        statement = select(MonthlyInsightRecap).where(
            MonthlyInsightRecap.user_id == user_id,
            MonthlyInsightRecap.month_key == month_key,
        )
        return self.db.scalar(statement)

    def upsert_for_user_month(
        self,
        *,
        existing: MonthlyInsightRecap | None,
        user_id: uuid.UUID,
        month_key: str,
        status: str,
        source_fingerprint: str,
        payload_json: dict[str, Any],
        generated_at: datetime,
    ) -> MonthlyInsightRecap:
        if existing is None:
            recap = MonthlyInsightRecap(
                user_id=user_id,
                month_key=month_key,
                status=status,
                source_fingerprint=source_fingerprint,
                payload_json=payload_json,
                generated_at=generated_at,
            )
            self.db.add(recap)
        else:
            recap = existing
            recap.status = status
            recap.source_fingerprint = source_fingerprint
            recap.payload_json = payload_json
            recap.generated_at = generated_at
            self.db.add(recap)

        self.db.flush()
        self.db.refresh(recap)
        return recap
