from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, cast

from conftest import TestingSessionLocal

from app.core.config import settings
from app.llm.bootstrap.seed_langfuse import bootstrap_datasets, bootstrap_prompts
from app.llm.eval_defs import (
    CATEGORY_CLASSIFIER_DATASET_NAME,
    MONTHLY_INSIGHT_RECAP_PROMPT_NAME,
    PDF_PARSER_DATASET_NAME,
    PDF_TRANSACTION_PARSER_PROMPT_NAME,
    TRANSACTION_CATEGORY_ASSISTANT_PROMPT_NAME,
)
from app.llm.evals.run_langfuse_evals import (
    build_promotion_gate,
    run_dataset,
    summarize_dataset_results,
)
from app.llm.evals.scorers import (
    score_category_classifier_case,
    score_pdf_parser_case,
)
from app.llm.observability import LangfuseObservabilityClient
from app.llm.prompt_provider import LangfusePromptProvider
from app.llm.types import FlowHandle, ResolvedPrompt
from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import AccountType, CategoryType
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.account_repository import AccountRepository
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.monthly_insight_recap_repository import MonthlyInsightRecapRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transactions import TransactionCategoryAssistantDraft
from app.services.azure_openai_monthly_recap_service import AzureOpenAIMonthlyRecapService
from app.services.azure_openai_pdf_parser_service import AzureOpenAIPdfParserService
from app.services.azure_openai_transaction_category_service import (
    AzureOpenAITransactionCategoryService,
)
from app.services.insights_service import InsightsService
from app.services.monthly_recap_service import MonthlyRecapService


@dataclass
class FakePromptClient:
    version: int = 7
    prompt: list[dict[str, str]] | None = None
    is_fallback: bool = False
    labels: list[str] | None = None

    def compile(self, **kwargs: str) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": "compiled system"},
            {"role": "user", "content": f"compiled {kwargs['structured_text']}"},
        ]


class FakeLangfuseForPromptProvider:
    def __init__(self, **_: object) -> None:
        self.created_prompts: list[dict[str, object]] = []
        self.created_datasets: list[dict[str, object]] = []
        self.created_dataset_items: list[dict[str, object]] = []

    def get_prompt(self, name: str, **_: object) -> FakePromptClient:
        return FakePromptClient(
            prompt=[{"type": "message", "role": "system", "content": "existing"}],
            labels=["production"],
        )

    def create_prompt(self, **kwargs: object) -> None:
        self.created_prompts.append(kwargs)

    def get_dataset(self, _: str) -> object:
        raise RuntimeError("dataset missing")

    def create_dataset(self, **kwargs: object) -> None:
        self.created_datasets.append(kwargs)

    def create_dataset_item(self, **kwargs: object) -> None:
        self.created_dataset_items.append(kwargs)

    def flush(self) -> None:
        return None


class FailingLangfuseForPromptProvider(FakeLangfuseForPromptProvider):
    def get_prompt(self, name: str, **_: object) -> FakePromptClient:
        raise RuntimeError(f"failed for {name}")


class FakeSpan:
    def __init__(self) -> None:
        self.id = "observation-id"
        self.trace_id = "trace-id"
        self.updates: list[dict[str, object]] = []
        self.ended = False

    def update(self, **kwargs: object) -> None:
        self.updates.append(kwargs)

    def end(self) -> None:
        self.ended = True


class FakeContextManager:
    def __init__(self) -> None:
        self.span = FakeSpan()

    def __enter__(self) -> FakeSpan:
        return self.span

    def __exit__(self, *_: object) -> None:
        return None


class FakeLangfuseForObservability(FakeLangfuseForPromptProvider):
    def __init__(self, **_: object) -> None:
        super().__init__()
        self.scores: list[dict[str, object]] = []

    def start_as_current_observation(self, **_: object) -> FakeContextManager:
        return FakeContextManager()

    def create_score(self, **kwargs: object) -> None:
        self.scores.append(kwargs)


class FailingLangfuseForObservability(FakeLangfuseForObservability):
    def start_as_current_observation(self, **_: object) -> FakeContextManager:
        raise RuntimeError("boom")


class RecordingObservabilityClient:
    def __init__(self) -> None:
        self.generations: list[dict[str, Any]] = []
        self.scores: list[dict[str, Any]] = []
        self.flows: list[FlowHandle] = []
        self.ended_flows: list[dict[str, Any]] = []

    def start_flow(
        self,
        name: str,
        *,
        input_payload: dict[str, object],
        metadata=None,
    ) -> FlowHandle:
        handle = FlowHandle(name=name, metadata=metadata or {}, input_payload=input_payload)
        self.flows.append(handle)
        return handle

    def end_flow(self, handle: FlowHandle, **kwargs: object) -> None:
        self.ended_flows.append({"handle": handle, **kwargs})
        return None

    def record_generation(self, **kwargs: object) -> None:
        self.generations.append(kwargs)

    def record_score(self, **kwargs: object) -> None:
        self.scores.append(kwargs)

    def flush(self) -> None:
        return None


class FakePromptProvider:
    def __init__(self, name: str) -> None:
        self.name = name

    def get_chat_prompt(
        self,
        name: str,
        *,
        label: str,
        variables: dict[str, object],
    ) -> ResolvedPrompt:
        assert name == self.name
        assert label == settings.langfuse_prompt_label
        return ResolvedPrompt(
            name=name,
            label=label,
            version=3,
            source="local_fallback",
            messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": str(variables)},
            ],
        )


class FakeHttpxResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.payload


class FakeHttpxClient:
    def __init__(self, payload: dict[str, object] | list[dict[str, object]]) -> None:
        if isinstance(payload, list):
            self.payloads = payload
        else:
            self.payloads = [payload]
        self.requests: list[dict[str, object]] = []

    def __enter__(self) -> "FakeHttpxClient":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
    ) -> FakeHttpxResponse:
        self.requests.append({"url": url, "headers": headers, "json": json})
        payload_index = min(len(self.requests) - 1, len(self.payloads) - 1)
        return FakeHttpxResponse(self.payloads[payload_index])


class FakeMonthlyNarrativeService:
    def generate_story_copy(self, **_: object) -> None:
        return None


def test_langfuse_prompt_provider_uses_remote_prompt(monkeypatch) -> None:
    monkeypatch.setattr("app.llm.prompt_provider.Langfuse", FakeLangfuseForPromptProvider)
    provider = LangfusePromptProvider(settings)

    resolved = provider.get_chat_prompt(
        PDF_TRANSACTION_PARSER_PROMPT_NAME,
        label="production",
        variables={"structured_text": "OCR", "tables_markdown": "TABLE"},
    )

    assert resolved.source == "langfuse"
    assert resolved.version == 7
    assert resolved.messages[1]["content"] == "compiled OCR"


def test_langfuse_prompt_provider_falls_back_on_error(monkeypatch) -> None:
    monkeypatch.setattr("app.llm.prompt_provider.Langfuse", FailingLangfuseForPromptProvider)
    provider = LangfusePromptProvider(settings)

    resolved = provider.get_chat_prompt(
        TRANSACTION_CATEGORY_ASSISTANT_PROMPT_NAME,
        label="production",
        variables={"category_payload": "[]", "row_payload": "[]"},
    )

    assert resolved.source == "local_fallback"
    assert "Available categories" in resolved.messages[1]["content"]


def test_langfuse_prompt_provider_fallback_renders_curly_variables(monkeypatch) -> None:
    monkeypatch.setattr("app.llm.prompt_provider.Langfuse", FailingLangfuseForPromptProvider)
    provider = LangfusePromptProvider(settings)

    resolved = provider.get_chat_prompt(
        MONTHLY_INSIGHT_RECAP_PROMPT_NAME,
        label="production",
        variables={
            "month_label": "abril 2026",
            "signals_payload": '{"expense_total":"1.200,00 EUR"}',
            "stories_payload": '[{"id":"top-category"}]',
        },
    )

    assert resolved.source == "local_fallback"
    content = resolved.messages[1]["content"]
    assert "abril 2026" in content
    assert '{"expense_total":"1.200,00 EUR"}' in content
    assert '[{"id":"top-category"}]' in content
    assert "{{month_label}}" not in content


def test_langfuse_observability_client_is_best_effort(monkeypatch) -> None:
    monkeypatch.setattr("app.llm.observability.Langfuse", FailingLangfuseForObservability)
    client = LangfuseObservabilityClient(settings)

    handle = client.start_flow("test_flow", input_payload={"a": 1}, metadata={"b": 2})
    client.record_generation(
        handle=handle,
        name="generation",
        model="gpt",
        prompt=ResolvedPrompt(
            name="p",
            label="production",
            version=None,
            source="local_fallback",
            messages=[],
        ),
        input_payload={"x": 1},
        output_payload={"y": 2},
    )
    client.end_flow(handle, output_payload={"done": True})
    client.flush()


def test_bootstrap_langfuse_dry_run_collects_actions() -> None:
    prompt_actions = bootstrap_prompts(None, label="production", dry_run=True)
    dataset_actions = bootstrap_datasets(None, dry_run=True)

    assert any(action.startswith("prompt:pdf-transaction-parser") for action in prompt_actions)
    assert any(action.startswith("dataset:pdf-transaction-parser-v1") for action in dataset_actions)


def test_eval_runner_dry_run_returns_perfect_scores() -> None:
    pdf_results = run_dataset(PDF_PARSER_DATASET_NAME, dry_run=True)
    category_results = run_dataset(CATEGORY_CLASSIFIER_DATASET_NAME, dry_run=True)

    assert all(item["score"] == 1.0 for item in pdf_results)
    assert all(item["score"] == 1.0 for item in category_results)
    assert all(item["scores"]["aggregate"] == 1.0 for item in pdf_results)
    assert all(item["scores"]["aggregate"] == 1.0 for item in category_results)
    assert all("row_recall" in item["scores"] for item in pdf_results)
    assert all("decision_quality" in item["scores"] for item in category_results)
    assert all("case_tags" in item for item in pdf_results)
    assert all("case_tags" in item for item in category_results)


def test_pdf_parser_scorer_penalizes_false_positives() -> None:
    scores = score_pdf_parser_case(
        actual_output={
            "transactions": [
                {
                    "Fecha": "2026-04-01",
                    "Descripción": "Servei d Activitat Fisica (SAF)",
                    "Importe": "-13.00",
                },
                {
                    "Fecha": "2026-04-99",
                    "Descripción": "Noise Footer Row",
                    "Importe": "-999.00",
                },
            ]
        },
        expected_output={
            "transactions": [
                {
                    "Fecha": "2026-04-01",
                    "Descripción": "Servei d Activitat Fisica (SAF)",
                    "Importe": "-13.00",
                }
            ],
            "allow_extra_transactions": False,
        },
    )

    assert scores["row_recall"] == 1.0
    assert scores["row_precision"] == 0.5
    assert scores["aggregate"] < 1.0


def test_category_classifier_scorer_rewards_safe_nulls() -> None:
    scores = score_category_classifier_case(
        actual_output={
            "category_name": None,
            "category_type": None,
            "confidence": None,
        },
        expected_output={
            "category_name": "Groceries",
            "allow_null": True,
            "expected_type": "expense",
        },
    )

    assert scores["null_behavior"] == 0.5
    assert scores["type_guardrail"] == 1.0
    assert scores["decision_quality"] == 0.5


def test_dataset_summary_aggregates_metrics_and_tags() -> None:
    summary = summarize_dataset_results(
        [
            {
                "case_name": "case_1",
                "scores": {"aggregate": 1.0, "row_recall": 1.0},
                "case_tags": ["happy_path", "structured_table"],
            },
            {
                "case_name": "case_2",
                "scores": {"aggregate": 0.5, "row_recall": 0.0},
                "case_tags": ["happy_path", "fallback"],
            },
        ]
    )

    assert summary["case_count"] == 2
    assert summary["metric_averages"]["aggregate"] == 0.75
    assert summary["metric_averages"]["row_recall"] == 0.5
    assert summary["tag_breakdown"]["happy_path"]["case_count"] == 2
    assert summary["tag_breakdown"]["happy_path"]["aggregate_average"] == 0.75
    assert summary["tag_breakdown"]["fallback"]["aggregate_average"] == 0.5


def test_promotion_gate_fails_when_critical_metric_is_below_threshold() -> None:
    gate = build_promotion_gate(
        PDF_PARSER_DATASET_NAME,
        {
            "metric_averages": {
                "aggregate": 0.96,
                "row_recall": 0.8,
                "amount_accuracy": 0.99,
            }
        },
    )

    assert gate["passed"] is False
    assert gate["checks"]["aggregate"]["passed"] is True
    assert gate["checks"]["row_recall"]["passed"] is False


def test_pdf_parser_service_records_generation(monkeypatch) -> None:
    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://example.com")
    monkeypatch.setattr(settings, "azure_openai_api_key", "secret")
    monkeypatch.setattr(settings, "azure_openai_pdf_parser_deployment", "pdf-deployment")

    fake_httpx = FakeHttpxClient(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"transactions":[{"date":"2026-04-02",'
                            '"description":"Ametller Origen","amount":"-2.09"}]}'
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
    )
    monkeypatch.setattr(
        "app.llm.azure_chat.httpx.Client",
        lambda timeout: fake_httpx,
    )

    observability_client = RecordingObservabilityClient()
    service = AzureOpenAIPdfParserService(
        prompt_provider=FakePromptProvider(PDF_TRANSACTION_PARSER_PROMPT_NAME),
        observability_client=observability_client,
    )

    rows = service.parse_transactions(structured_text="OCR", tables_markdown="TABLE")

    assert rows[0]["Descripción"] == "Ametller Origen"
    assert observability_client.generations[0]["model"] == "pdf-deployment"


def test_category_service_records_generation(monkeypatch) -> None:
    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://example.com")
    monkeypatch.setattr(settings, "azure_openai_api_key", "secret")
    monkeypatch.setattr(settings, "azure_openai_transaction_category_deployment", "cat-deployment")

    fake_httpx = FakeHttpxClient(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"suggestions":[{"source_row_number":1,'
                            '"category_id":null,"confidence":0.2}]}'
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
        }
    )
    monkeypatch.setattr(
        "app.llm.azure_chat.httpx.Client",
        lambda timeout: fake_httpx,
    )

    observability_client = RecordingObservabilityClient()
    service = AzureOpenAITransactionCategoryService(
        prompt_provider=FakePromptProvider(TRANSACTION_CATEGORY_ASSISTANT_PROMPT_NAME),
        observability_client=observability_client,
    )

    suggestions = service.classify_rows(
        rows=[
            TransactionCategoryAssistantDraft(
                source_row_number=1,
                description="Corner Shop",
                notes=None,
                amount=Decimal("-9.90"),
                currency="EUR",
            )
        ],
        categories=cast(
            Any,
            [
                type(
                    "FakeCategory",
                    (),
                    {
                        "id": "cat-1",
                        "name": "Groceries",
                        "type": type("FakeType", (), {"value": "expense"})(),
                    },
                )()
            ],
        ),
    )

    assert suggestions[0].source_row_number == 1
    assert observability_client.generations[0]["model"] == "cat-deployment"


def test_category_service_returns_empty_list_on_invalid_model_payload(monkeypatch) -> None:
    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://example.com")
    monkeypatch.setattr(settings, "azure_openai_api_key", "secret")
    monkeypatch.setattr(settings, "azure_openai_transaction_category_deployment", "cat-deployment")

    fake_httpx = FakeHttpxClient(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"suggestions":[{"source_row_number":null,'
                            '"category_id":null,"confidence":0.2}]}'
                        )
                    }
                }
            ]
        }
    )
    monkeypatch.setattr(
        "app.llm.azure_chat.httpx.Client",
        lambda timeout: fake_httpx,
    )

    observability_client = RecordingObservabilityClient()
    service = AzureOpenAITransactionCategoryService(
        prompt_provider=FakePromptProvider(TRANSACTION_CATEGORY_ASSISTANT_PROMPT_NAME),
        observability_client=observability_client,
    )

    suggestions = service.classify_rows(
        rows=[
            TransactionCategoryAssistantDraft(
                source_row_number=1,
                description="Corner Shop",
                notes=None,
                amount=Decimal("-9.90"),
                currency="EUR",
            )
        ],
        categories=cast(
            Any,
            [
                type(
                    "FakeCategory",
                    (),
                    {
                        "id": "cat-1",
                        "name": "Groceries",
                        "type": type("FakeType", (), {"value": "expense"})(),
                    },
                )()
            ],
        ),
    )

    assert suggestions == []
    assert (
        observability_client.generations[0]["status_message"]
        == "Invalid classifier response payload"
    )


def test_monthly_recap_generation_records_langfuse_generation(monkeypatch) -> None:
    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://example.com")
    monkeypatch.setattr(settings, "azure_openai_api_key", "secret")
    monkeypatch.setattr(settings, "azure_openai_monthly_recap_deployment", "recap-deployment")

    fake_httpx = FakeHttpxClient(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"stories":[{"id":"top-category","headline":"Headline",'
                            '"subheadline":"Subheadline","body":"Body"}]}'
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 9, "completion_tokens": 7, "total_tokens": 16},
        }
    )
    monkeypatch.setattr("app.llm.azure_chat.httpx.Client", lambda timeout: fake_httpx)

    observability_client = RecordingObservabilityClient()
    service = AzureOpenAIMonthlyRecapService(
        prompt_provider=FakePromptProvider(MONTHLY_INSIGHT_RECAP_PROMPT_NAME),
        observability_client=observability_client,
    )

    stories = service.generate_story_copy(
        month_label="marzo 2026",
        signals_payload={"expense_total": "100.00 EUR"},
        stories_payload=[{"id": "top-category", "title": "Top spending category"}],
        handle=FlowHandle(name="flow", metadata={}, input_payload={}),
    )

    assert stories is not None
    assert stories["top-category"].headline == "Headline"
    assert observability_client.generations[0]["model"] == "recap-deployment"


def test_monthly_recap_generation_rejects_empty_story_payload(monkeypatch) -> None:
    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://example.com")
    monkeypatch.setattr(settings, "azure_openai_api_key", "secret")
    monkeypatch.setattr(settings, "azure_openai_monthly_recap_deployment", "recap-deployment")

    fake_httpx = FakeHttpxClient(
        {
            "choices": [{"message": {"content": '{"stories":[]}'}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 4, "total_tokens": 11},
        }
    )
    monkeypatch.setattr("app.llm.azure_chat.httpx.Client", lambda timeout: fake_httpx)

    observability_client = RecordingObservabilityClient()
    service = AzureOpenAIMonthlyRecapService(
        prompt_provider=FakePromptProvider(MONTHLY_INSIGHT_RECAP_PROMPT_NAME),
        observability_client=observability_client,
    )

    stories = service.generate_story_copy(
        month_label="marzo 2026",
        signals_payload={"expense_total": "100.00 EUR"},
        stories_payload=[{"id": "top-category", "title": "Categoría principal"}],
        handle=FlowHandle(name="flow", metadata={}, input_payload={}),
    )

    assert stories is None
    assert (
        observability_client.generations[0]["status_message"]
        == "Invalid monthly recap response payload"
    )
    metadata = cast(dict[str, Any], observability_client.generations[0]["metadata"])
    assert metadata["invalid_reason"] == "llm_empty_stories"


def test_monthly_recap_generation_retries_with_stricter_prompt(monkeypatch) -> None:
    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://example.com")
    monkeypatch.setattr(settings, "azure_openai_api_key", "secret")
    monkeypatch.setattr(settings, "azure_openai_monthly_recap_deployment", "recap-deployment")

    fake_httpx = FakeHttpxClient(
        [
            {
                "choices": [{"message": {"content": '{"stories":[]}'}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 4, "total_tokens": 11},
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"stories":[{"id":"top-category","headline":"Headline",'
                                '"subheadline":"Subheadline","body":"Body"}]}'
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 9, "completion_tokens": 7, "total_tokens": 16},
            },
        ]
    )
    monkeypatch.setattr("app.llm.azure_chat.httpx.Client", lambda timeout: fake_httpx)

    observability_client = RecordingObservabilityClient()
    service = AzureOpenAIMonthlyRecapService(
        prompt_provider=FakePromptProvider(MONTHLY_INSIGHT_RECAP_PROMPT_NAME),
        observability_client=observability_client,
    )

    stories = service.generate_story_copy(
        month_label="marzo 2026",
        signals_payload={"expense_total": "100.00 EUR"},
        stories_payload=[{"id": "top-category", "title": "Categoría principal"}],
        handle=FlowHandle(name="flow", metadata={}, input_payload={}),
    )

    assert stories is not None
    assert stories["top-category"].headline == "Headline"
    assert len(fake_httpx.requests) == 2
    second_request_json = cast(dict[str, object], fake_httpx.requests[1]["json"])
    assert second_request_json["temperature"] == 0
    metadata = cast(dict[str, Any], observability_client.generations[0]["metadata"])
    assert metadata["retried"] is True
    assert metadata["attempt_count"] == 2


def test_monthly_recap_service_records_cache_hit_flow() -> None:
    observability_client = RecordingObservabilityClient()

    with TestingSessionLocal() as db:
        user = User(
            auth_provider_user_id=f"test-{Decimal('1.0')}",
            email="monthly-recap@example.com",
            name="Monthly Recap",
        )
        db.add(user)
        db.flush()

        account = Account(
            user_id=user.id,
            name="Main",
            bank_name="Demo",
            type=AccountType.CHECKING,
            currency="EUR",
        )
        category = Category(
            user_id=user.id,
            name="Food",
            type=CategoryType.EXPENSE,
            color="#f97316",
            icon="utensils",
        )
        budget = Budget(
            user_id=user.id,
            category_id=category.id,
            year=2026,
            month=3,
            currency="EUR",
            amount=Decimal("200.00"),
        )
        transaction = Transaction(
            user_id=user.id,
            account_id=account.id,
            category_id=category.id,
            date=date(2026, 3, 12),
            amount=Decimal("-42.50"),
            currency="EUR",
            description="Mercado",
            notes=None,
        )

        db.add_all([account, category])
        db.flush()
        budget.category_id = category.id
        transaction.account_id = account.id
        transaction.category_id = category.id
        db.add_all([budget, transaction])
        db.commit()

        recap_service = MonthlyRecapService(
            insights_service=InsightsService(
                AccountRepository(db),
                CategoryRepository(db),
                TransactionRepository(db),
            ),
            budget_repository=BudgetRepository(db),
            recap_repository=MonthlyInsightRecapRepository(db),
            db=db,
            prompt_provider=FakePromptProvider(MONTHLY_INSIGHT_RECAP_PROMPT_NAME),
            observability_client=observability_client,
            narrative_service=FakeMonthlyNarrativeService(),
        )

        first = recap_service.get_monthly_recap(user_id=user.id, month_key="2026-03")
        second = recap_service.get_monthly_recap(user_id=user.id, month_key="2026-03")

    assert first.status == "fallback"
    assert second.generated_at == first.generated_at
    assert observability_client.ended_flows[0]["metadata"]["cache_status"] == "generated"
    assert observability_client.ended_flows[1]["metadata"]["cache_status"] == "hit"
