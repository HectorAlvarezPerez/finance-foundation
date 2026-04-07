from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal, Protocol, cast

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.llm.runtime import build_llm_runtime
from app.llm.types import FlowHandle, LlmObservabilityClient, PromptProvider
from app.models.budget import Budget
from app.models.monthly_insight_recap import MonthlyInsightRecap
from app.models.transaction import Transaction
from app.repositories.budget_repository import BudgetRepository
from app.repositories.monthly_insight_recap_repository import MonthlyInsightRecapRepository
from app.schemas.insights import (
    InsightsMonthlyRecapFactRead,
    InsightsMonthlyRecapRead,
    InsightsMonthlyRecapStoryRead,
    InsightsMonthlyRecapVisualDatumRead,
    InsightsMonthlyRecapVisualRead,
)
from app.services.azure_openai_monthly_recap_service import (
    AzureOpenAIMonthlyRecapService,
    MonthlyRecapNarrativeStory,
)
from app.services.insights_service import InsightsService

MONTH_KEY_PATTERN = re.compile(r"^\d{4}-\d{2}$")
ZERO = Decimal("0.00")


@dataclass(frozen=True)
class MonthWindow:
    month_key: str
    year: int
    month: int
    month_label: str
    previous_month_key: str
    previous_year: int
    previous_month: int
    previous_month_label: str


class MonthlyRecapNarrativeClient(Protocol):
    def generate_story_copy(
        self,
        *,
        month_label: str,
        signals_payload: dict[str, Any],
        stories_payload: list[dict[str, Any]],
        handle: FlowHandle | None,
    ) -> dict[str, MonthlyRecapNarrativeStory] | None: ...


class MonthlyRecapService:
    def __init__(
        self,
        *,
        insights_service: InsightsService,
        budget_repository: BudgetRepository,
        recap_repository: MonthlyInsightRecapRepository,
        db: Session,
        prompt_provider: PromptProvider | None = None,
        observability_client: LlmObservabilityClient | None = None,
        narrative_service: MonthlyRecapNarrativeClient | None = None,
    ) -> None:
        runtime = build_llm_runtime()
        self.insights_service = insights_service
        self.budget_repository = budget_repository
        self.recap_repository = recap_repository
        self.db = db
        self.prompt_provider = prompt_provider or runtime.prompt_provider
        self.observability_client = observability_client or runtime.observability_client
        self.narrative_service = narrative_service or AzureOpenAIMonthlyRecapService(
            prompt_provider=self.prompt_provider,
            observability_client=self.observability_client,
        )

    def get_monthly_recap(
        self,
        *,
        user_id: uuid.UUID,
        month_key: str,
    ) -> InsightsMonthlyRecapRead:
        return self._load_or_generate_recap(
            user_id=user_id,
            month_key=month_key,
            force_regenerate=False,
        )

    def regenerate_monthly_recap(
        self,
        *,
        user_id: uuid.UUID,
        month_key: str,
    ) -> InsightsMonthlyRecapRead:
        return self._load_or_generate_recap(
            user_id=user_id,
            month_key=month_key,
            force_regenerate=True,
        )

    def _load_or_generate_recap(
        self,
        *,
        user_id: uuid.UUID,
        month_key: str,
        force_regenerate: bool,
    ) -> InsightsMonthlyRecapRead:
        window = self._parse_month_key(month_key)
        flow = self.observability_client.start_flow(
            "monthly_insight_recap_generation",
            input_payload={
                "month_key": month_key,
                "force_regenerate": force_regenerate,
            },
            metadata={"user_id": str(user_id), "month_key": month_key},
        )

        try:
            snapshot = self.insights_service.get_snapshot(user_id=user_id)
            current_transactions = self._filter_month_transactions(
                snapshot.transactions,
                year=window.year,
                month=window.month,
            )
            previous_transactions = self._filter_month_transactions(
                snapshot.transactions,
                year=window.previous_year,
                month=window.previous_month,
            )
            budgets = self.budget_repository.list_all_for_user(
                user_id=user_id,
                year=window.year,
                month=window.month,
                sort_by="month",
                sort_order="asc",
            )

            existing = self.recap_repository.get_for_user_and_month(
                user_id=user_id,
                month_key=month_key,
            )
            fingerprint = self._build_source_fingerprint(
                accounts=snapshot.accounts,
                categories=snapshot.categories,
                transactions=current_transactions,
                budgets=budgets,
                month_key=month_key,
            )

            if existing is not None and not force_regenerate:
                if existing.source_fingerprint == fingerprint:
                    recap = self._to_read_model(existing, is_stale=False)
                    self._end_flow(
                        flow,
                        cache_status="hit",
                        source_fingerprint=fingerprint,
                        story_kinds=[story.kind for story in recap.stories],
                        used_fallback=recap.status == "fallback",
                        output_payload={
                            "story_count": len(recap.stories),
                            "status": recap.status,
                            "is_stale": False,
                        },
                    )
                    return recap

                recap = self._to_read_model(existing, is_stale=True)
                self._end_flow(
                    flow,
                    cache_status="stale",
                    source_fingerprint=fingerprint,
                    story_kinds=[story.kind for story in recap.stories],
                    used_fallback=recap.status == "fallback",
                    output_payload={
                        "story_count": len(recap.stories),
                        "status": recap.status,
                        "is_stale": True,
                    },
                    status_message="Serving stale recap",
                    level="WARNING",
                )
                return recap

            if not current_transactions and existing is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No recap data available for the selected month",
                )

            payload_json, status_value = self._generate_payload(
                window=window,
                current_transactions=current_transactions,
                previous_transactions=previous_transactions,
                budgets=budgets,
                categories=snapshot.categories,
                flow=flow,
            )
            generated_at = datetime.now(timezone.utc)
            persisted = self.recap_repository.upsert_for_user_month(
                existing=existing,
                user_id=user_id,
                month_key=month_key,
                status=status_value,
                source_fingerprint=fingerprint,
                payload_json=payload_json,
                generated_at=generated_at,
            )
            self.db.commit()

            recap = self._to_read_model(persisted, is_stale=False)
            self._end_flow(
                flow,
                cache_status="regenerated" if existing is not None else "generated",
                source_fingerprint=fingerprint,
                story_kinds=[story.kind for story in recap.stories],
                used_fallback=recap.status == "fallback",
                output_payload={
                    "story_count": len(recap.stories),
                    "status": recap.status,
                    "is_stale": False,
                },
            )
            return recap
        except HTTPException:
            self.db.rollback()
            self._end_flow(
                flow,
                cache_status="error",
                source_fingerprint=None,
                story_kinds=[],
                used_fallback=False,
                output_payload=None,
                status_message="Recap request failed",
                level="ERROR",
            )
            raise
        except Exception as exc:
            self.db.rollback()
            self._end_flow(
                flow,
                cache_status="error",
                source_fingerprint=None,
                story_kinds=[],
                used_fallback=False,
                output_payload=None,
                status_message=str(exc),
                level="ERROR",
            )
            raise

    def _generate_payload(
        self,
        *,
        window: MonthWindow,
        current_transactions: list[Transaction],
        previous_transactions: list[Transaction],
        budgets: list[Budget],
        categories: list[Any],
        flow: FlowHandle,
    ) -> tuple[dict[str, Any], str]:
        category_map = {str(category.id): category for category in categories}
        signals = self._build_signals(
            window=window,
            current_transactions=current_transactions,
            previous_transactions=previous_transactions,
            budgets=budgets,
            category_map=category_map,
        )
        drafts = self._build_story_drafts(signals=signals, category_map=category_map)

        llm_output = self.narrative_service.generate_story_copy(
            month_label=window.month_label,
            signals_payload=self._build_llm_signals_payload(signals),
            stories_payload=self._build_llm_story_payloads(drafts),
            handle=flow,
        )

        used_fallback = False
        stories: list[InsightsMonthlyRecapStoryRead] = []
        for draft in drafts:
            narrative = llm_output.get(draft["id"]) if llm_output is not None else None
            if narrative is None:
                used_fallback = True
                narrative = MonthlyRecapNarrativeStory(
                    id=draft["id"],
                    headline=draft["fallback_headline"],
                    subheadline=draft["fallback_subheadline"],
                    body=draft["fallback_body"],
                )

            stories.append(
                InsightsMonthlyRecapStoryRead(
                    id=draft["id"],
                    kind=draft["kind"],
                    theme=draft["theme"],
                    title=draft["title"],
                    headline=narrative.headline,
                    subheadline=narrative.subheadline,
                    body=narrative.body,
                    facts=draft["facts"],
                    visual=draft["visual"],
                )
            )

        return (
            {
                "schema_version": 1,
                "month_label": window.month_label,
                "stories": [story.model_dump(mode="json") for story in stories],
            },
            "fallback" if used_fallback else "ready",
        )

    def _build_signals(
        self,
        *,
        window: MonthWindow,
        current_transactions: list[Transaction],
        previous_transactions: list[Transaction],
        budgets: list[Budget],
        category_map: dict[str, Any],
    ) -> dict[str, Any]:
        income_total = sum(
            (transaction.amount for transaction in current_transactions if transaction.amount >= 0),
            start=ZERO,
        )
        expense_total = sum(
            (
                abs(transaction.amount)
                for transaction in current_transactions
                if transaction.amount < 0
            ),
            start=ZERO,
        )
        net_total = sum((transaction.amount for transaction in current_transactions), start=ZERO)
        previous_expense_total = sum(
            (
                abs(transaction.amount)
                for transaction in previous_transactions
                if transaction.amount < 0
            ),
            start=ZERO,
        )

        expense_by_category: defaultdict[str | None, Decimal] = defaultdict(lambda: ZERO)
        category_transaction_counts: defaultdict[str | None, int] = defaultdict(int)
        for transaction in current_transactions:
            if transaction.amount >= 0:
                continue
            category_key = (
                str(transaction.category_id) if transaction.category_id is not None else None
            )
            expense_by_category[category_key] += abs(transaction.amount)
            category_transaction_counts[category_key] += 1

        top_category_key, top_category_total = self._pick_top_category(expense_by_category)
        top_category = category_map.get(top_category_key) if top_category_key is not None else None

        biggest_moment = self._pick_biggest_moment(current_transactions)
        budget_total = sum((budget.amount for budget in budgets), start=ZERO)
        delta_expenses = expense_total - previous_expense_total
        delta_percentage = self._percentage_delta(expense_total, previous_expense_total)

        return {
            "month_key": window.month_key,
            "month_label": window.month_label,
            "previous_month_key": window.previous_month_key,
            "current": {
                "transaction_count": len(current_transactions),
                "income_total": income_total,
                "expense_total": expense_total,
                "net_total": net_total,
                "budget_total": budget_total,
            },
            "comparison": {
                "expense_total_previous": previous_expense_total,
                "delta_expenses": delta_expenses,
                "delta_percentage": delta_percentage,
                "previous_month_label": window.previous_month_label,
            },
            "top_category": {
                "id": top_category_key,
                "name": top_category.name if top_category is not None else "Sin categoría",
                "color": (
                    top_category.color
                    if top_category is not None and top_category.color
                    else "#f59e0b"
                ),
                "total": top_category_total,
                "transaction_count": category_transaction_counts.get(top_category_key, 0),
                "share_of_expenses": self._safe_ratio(top_category_total, expense_total),
            },
            "biggest_moment": biggest_moment,
            "top_category_points": [
                {
                    "label": (
                        category_map[str(category_id)].name
                        if category_id is not None and str(category_id) in category_map
                        else "Sin categoría"
                    ),
                    "value": total,
                    "color": (
                        category_map[str(category_id)].color
                        if category_id is not None
                        and str(category_id) in category_map
                        and category_map[str(category_id)].color
                        else "#94a3b8"
                    ),
                    "emphasized": index == 0,
                    "note": f"#{index + 1}",
                }
                for index, (category_id, total) in enumerate(
                    sorted(
                        expense_by_category.items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )[:4]
                )
            ],
        }

    def _build_story_drafts(
        self,
        *,
        signals: dict[str, Any],
        category_map: dict[str, Any],
    ) -> list[dict[str, Any]]:
        top_category = signals["top_category"]
        biggest_moment = signals["biggest_moment"]
        comparison = signals["comparison"]
        current = signals["current"]

        share_percentage = self._percent_to_display(top_category["share_of_expenses"])
        top_category_facts = [
            InsightsMonthlyRecapFactRead(
                label="Gasto",
                value=self._money_display(top_category["total"]),
                tone="negative",
            ),
            InsightsMonthlyRecapFactRead(
                label="Peso del mes",
                value=share_percentage,
                tone="accent",
            ),
            InsightsMonthlyRecapFactRead(
                label="Movimientos",
                value=str(top_category["transaction_count"]),
                tone="neutral",
            ),
        ]
        biggest_moment_facts = [
            InsightsMonthlyRecapFactRead(
                label="Fecha",
                value=biggest_moment["date_label"],
                tone="neutral",
            ),
            InsightsMonthlyRecapFactRead(
                label="Categoría",
                value=biggest_moment["category_name"],
                tone="accent",
            ),
            InsightsMonthlyRecapFactRead(
                label="Impacto",
                value=self._money_display(biggest_moment["amount_abs"]),
                tone="negative" if biggest_moment["amount"] < 0 else "positive",
            ),
        ]
        comparison_facts = [
            InsightsMonthlyRecapFactRead(
                label="Este mes",
                value=self._money_display(current["expense_total"]),
                tone="negative",
            ),
            InsightsMonthlyRecapFactRead(
                label=signals["comparison"]["previous_month_label"],
                value=self._money_display(comparison["expense_total_previous"]),
                tone="neutral",
            ),
            InsightsMonthlyRecapFactRead(
                label="Delta",
                value=self._signed_money_display(comparison["delta_expenses"]),
                tone="positive" if comparison["delta_expenses"] <= 0 else "negative",
            ),
        ]

        top_category_name = top_category["name"]
        biggest_moment_title = "Biggest spending moment"
        comparison_title = "Comparison vs previous month"
        top_category_title = "Top spending category"

        return [
            {
                "id": "top-category",
                "kind": "top_category",
                "theme": "amber",
                "title": top_category_title,
                "facts": top_category_facts,
                "visual": InsightsMonthlyRecapVisualRead(
                    kind="top_category",
                    amount=top_category["total"],
                    share=(
                        float(top_category["share_of_expenses"] * Decimal("100"))
                        if top_category["share_of_expenses"] is not None
                        else None
                    ),
                    category_name=top_category["name"],
                    category_color=top_category["color"],
                    series=[
                        InsightsMonthlyRecapVisualDatumRead(
                            label=point["label"],
                            value=point["value"],
                            color=point["color"],
                        )
                        for point in signals["top_category_points"]
                    ],
                    accent_color=top_category["color"],
                ),
                "fallback_headline": (
                    f"{top_category_name} dominó {signals['month_label']}"
                    if top_category["total"] > 0
                    else f"{signals['month_label']} cerró sin un gasto dominante"
                ),
                "fallback_subheadline": (
                    f"Concentró {share_percentage} del gasto del mes."
                    if top_category["total"] > 0
                    else "No hubo un patrón de gasto claro en categorías."
                ),
                "fallback_body": (
                    f"{top_category_name} sumó {self._money_display(top_category['total'])} "
                    f"repartidos en {top_category['transaction_count']} movimientos."
                    if top_category["total"] > 0
                    else (
                        "La actividad del mes fue demasiado ligera para destacar una "
                        "categoría de gasto."
                    )
                ),
            },
            {
                "id": "biggest-moment",
                "kind": "biggest_moment",
                "theme": "rose" if biggest_moment["amount"] < 0 else "sky",
                "title": biggest_moment_title,
                "facts": biggest_moment_facts,
                "visual": InsightsMonthlyRecapVisualRead(
                    kind="biggest_moment",
                    amount=biggest_moment["amount_abs"],
                    date_label=biggest_moment["date_label"],
                    description=(
                        f"Registrado en {biggest_moment['category_name'].lower()} "
                        f"como uno de los momentos que más marcaron el mes."
                    ),
                    merchant=biggest_moment["description"],
                    accent_color=biggest_moment["color"],
                ),
                "fallback_headline": biggest_moment["fallback_headline"],
                "fallback_subheadline": biggest_moment["fallback_subheadline"],
                "fallback_body": biggest_moment["fallback_body"],
            },
            {
                "id": "month-comparison",
                "kind": "month_comparison",
                "theme": "lime" if comparison["delta_expenses"] <= 0 else "sky",
                "title": comparison_title,
                "facts": comparison_facts,
                "visual": InsightsMonthlyRecapVisualRead(
                    kind="month_comparison",
                    accent_color="#38bdf8" if comparison["delta_expenses"] > 0 else "#84cc16",
                    current_amount=current["expense_total"],
                    previous_amount=comparison["expense_total_previous"],
                    delta=comparison["delta_expenses"],
                    current_label=signals["month_label"],
                    previous_label=signals["comparison"]["previous_month_label"],
                    current_color="#f97316",
                    previous_color="rgba(255,255,255,0.34)",
                ),
                "fallback_headline": self._comparison_fallback_headline(signals),
                "fallback_subheadline": self._comparison_fallback_subheadline(signals),
                "fallback_body": self._comparison_fallback_body(signals),
            },
        ]

    def _build_llm_signals_payload(self, signals: dict[str, Any]) -> dict[str, Any]:
        return {
            "month_label": signals["month_label"],
            "transaction_count": signals["current"]["transaction_count"],
            "income_total": self._money_display(signals["current"]["income_total"]),
            "expense_total": self._money_display(signals["current"]["expense_total"]),
            "net_total": self._money_display(signals["current"]["net_total"]),
            "top_category_name": signals["top_category"]["name"],
            "top_category_total": self._money_display(signals["top_category"]["total"]),
            "top_category_share": self._percent_to_display(
                signals["top_category"]["share_of_expenses"]
            ),
            "biggest_moment_description": signals["biggest_moment"]["description"],
            "biggest_moment_amount": self._money_display(signals["biggest_moment"]["amount_abs"]),
            "comparison_previous_month": signals["comparison"]["previous_month_label"],
            "comparison_delta": self._signed_money_display(signals["comparison"]["delta_expenses"]),
            "comparison_delta_percentage": self._percent_to_display(
                signals["comparison"]["delta_percentage"]
            ),
        }

    def _build_llm_story_payloads(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": draft["id"],
                "kind": draft["kind"],
                "title": draft["title"],
                "facts": [fact.model_dump(mode="json") for fact in draft["facts"]],
                "fallback_headline": draft["fallback_headline"],
                "fallback_subheadline": draft["fallback_subheadline"],
                "fallback_body": draft["fallback_body"],
            }
            for draft in drafts
        ]

    def _build_source_fingerprint(
        self,
        *,
        accounts: list[Any],
        categories: list[Any],
        transactions: list[Transaction],
        budgets: list[Budget],
        month_key: str,
    ) -> str:
        payload = {
            "month_key": month_key,
            "transaction_count": len(transactions),
            "transaction_max_updated_at": self._max_updated_at(transactions),
            "account_count": len(accounts),
            "account_max_updated_at": self._max_updated_at(accounts),
            "category_count": len(categories),
            "category_max_updated_at": self._max_updated_at(categories),
            "budget_count": len(budgets),
            "budget_max_updated_at": self._max_updated_at(budgets),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    def _parse_month_key(self, month_key: str) -> MonthWindow:
        if not MONTH_KEY_PATTERN.fullmatch(month_key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="month_key must use YYYY-MM format",
            )

        year = int(month_key[:4])
        month = int(month_key[5:7])
        if month < 1 or month > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="month_key must use a valid calendar month",
            )

        if month == 1:
            previous_year = year - 1
            previous_month = 12
        else:
            previous_year = year
            previous_month = month - 1

        previous_month_key = f"{previous_year}-{previous_month:02d}"
        return MonthWindow(
            month_key=month_key,
            year=year,
            month=month,
            month_label=self.insights_service.format_month_label_parts(year, month),
            previous_month_key=previous_month_key,
            previous_year=previous_year,
            previous_month=previous_month,
            previous_month_label=self.insights_service.format_month_label_parts(
                previous_year,
                previous_month,
            ),
        )

    def _filter_month_transactions(
        self,
        transactions: list[Transaction],
        *,
        year: int,
        month: int,
    ) -> list[Transaction]:
        return [
            transaction
            for transaction in transactions
            if transaction.date.year == year and transaction.date.month == month
        ]

    def _pick_top_category(
        self,
        expense_by_category: dict[str | None, Decimal],
    ) -> tuple[str | None, Decimal]:
        if not expense_by_category:
            return None, ZERO

        category_key, total = max(expense_by_category.items(), key=lambda item: item[1])
        return category_key, total

    def _pick_biggest_moment(self, transactions: list[Transaction]) -> dict[str, Any]:
        if not transactions:
            return {
                "description": "Actividad muy ligera",
                "amount": ZERO,
                "amount_abs": ZERO,
                "category_name": "Sin categoría",
                "date_label": "Sin datos",
                "color": "#64748b",
                "fallback_headline": "Un mes de actividad contenida",
                "fallback_subheadline": "No apareció un gasto especialmente dominante.",
                "fallback_body": (
                    "El recap sigue disponible, pero este mes no dejó un momento de "
                    "gasto especialmente marcado."
                ),
            }

        expense_transactions = [
            transaction for transaction in transactions if transaction.amount < 0
        ]
        if expense_transactions:
            selected = min(expense_transactions, key=lambda transaction: transaction.amount)
            tone = "gasto"
        else:
            selected = max(transactions, key=lambda transaction: abs(transaction.amount))
            tone = "movimiento"

        amount_abs = abs(selected.amount)
        category_name = "Sin categoría"
        color = "#fb7185" if selected.amount < 0 else "#38bdf8"
        if selected.category is not None:
            category_name = selected.category.name
            if selected.category.color:
                color = selected.category.color

        description = selected.description.strip() or "Movimiento sin descripción"
        date_label = selected.date.strftime("%d %b")
        return {
            "description": description,
            "amount": selected.amount,
            "amount_abs": amount_abs,
            "category_name": category_name,
            "date_label": date_label,
            "color": color,
            "fallback_headline": f"{description} fue el {tone} que más se hizo notar",
            "fallback_subheadline": (
                f"Golpeó el mes el {date_label.lower()} con {self._money_display(amount_abs)}."
            ),
            "fallback_body": (
                f"Se registró en {category_name.lower()} y terminó siendo el punto "
                "más intenso del mes."
            ),
        }

    def _comparison_fallback_headline(self, signals: dict[str, Any]) -> str:
        delta = signals["comparison"]["delta_expenses"]
        previous_label = signals["comparison"]["previous_month_label"]
        if delta > 0:
            return f"El gasto subió frente a {previous_label}"
        if delta < 0:
            return f"El gasto bajó frente a {previous_label}"
        return f"El gasto quedó plano frente a {previous_label}"

    def _comparison_fallback_subheadline(self, signals: dict[str, Any]) -> str:
        delta_display = self._signed_money_display(signals["comparison"]["delta_expenses"])
        delta_percentage = self._percent_to_display(signals["comparison"]["delta_percentage"])
        return f"El cambio fue de {delta_display} ({delta_percentage})."

    def _comparison_fallback_body(self, signals: dict[str, Any]) -> str:
        current = self._money_display(signals["current"]["expense_total"])
        previous = self._money_display(signals["comparison"]["expense_total_previous"])
        return f"Este mes cerró en {current} de gasto frente a {previous} del mes anterior."

    def _to_read_model(
        self,
        recap: MonthlyInsightRecap,
        *,
        is_stale: bool,
    ) -> InsightsMonthlyRecapRead:
        payload = recap.payload_json or {}
        return InsightsMonthlyRecapRead(
            month_key=recap.month_key,
            month_label=str(payload.get("month_label", recap.month_key)),
            status=cast(Literal["ready", "fallback"], recap.status),
            generated_at=recap.generated_at,
            is_stale=is_stale,
            stories=[
                InsightsMonthlyRecapStoryRead.model_validate(story)
                for story in payload.get("stories", [])
            ],
        )

    def _end_flow(
        self,
        handle: FlowHandle,
        *,
        cache_status: str,
        source_fingerprint: str | None,
        story_kinds: list[str],
        used_fallback: bool,
        output_payload: dict[str, Any] | None,
        status_message: str | None = None,
        level: str | None = None,
    ) -> None:
        self.observability_client.end_flow(
            handle,
            output_payload=output_payload,
            metadata={
                "cache_status": cache_status,
                "source_fingerprint": source_fingerprint,
                "story_kinds": story_kinds,
                "used_fallback": used_fallback,
            },
            status_message=status_message,
            level=level,
        )

    def _max_updated_at(self, items: list[Any]) -> str | None:
        timestamps: list[datetime] = []
        for item in items:
            value = getattr(item, "updated_at", None)
            if isinstance(value, datetime):
                timestamps.append(value)
        if not timestamps:
            return None
        return max(timestamps).isoformat()

    def _safe_ratio(self, numerator: Decimal, denominator: Decimal) -> Decimal | None:
        if denominator == 0:
            return None
        return (numerator / denominator).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    def _percentage_delta(self, current: Decimal, previous: Decimal) -> Decimal | None:
        if previous == 0:
            return None
        return ((current - previous) / previous).quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP,
        )

    def _percent_to_display(self, ratio: Decimal | None) -> str:
        if ratio is None:
            return "n/a"
        return f"{(ratio * Decimal('100')).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%"

    def _money_display(self, amount: Decimal) -> str:
        return f"{amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)} EUR"

    def _signed_money_display(self, amount: Decimal) -> str:
        quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        prefix = "+" if quantized > 0 else ""
        return f"{prefix}{quantized} EUR"
