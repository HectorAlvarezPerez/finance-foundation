from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.llm.azure_chat import AzureChatCompletionClient
from app.llm.eval_defs import TRANSACTION_CATEGORY_ASSISTANT_PROMPT_NAME
from app.llm.prompt_variables import build_category_classifier_variables
from app.llm.runtime import build_observability_client, build_prompt_provider
from app.llm.types import LlmObservabilityClient, PromptProvider
from app.models.category import Category
from app.schemas.transactions import (
    TransactionCategoryAssistantDraft,
    TransactionCategoryAssistantResponse,
    TransactionCategoryAssistantSuggestion,
)


class AzureOpenAITransactionCategoryService:
    def __init__(
        self,
        *,
        chat_client: AzureChatCompletionClient | None = None,
        prompt_provider: PromptProvider | None = None,
        observability_client: LlmObservabilityClient | None = None,
    ) -> None:
        self.chat_client = chat_client or AzureChatCompletionClient(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_transaction_category_deployment,
            api_version=settings.azure_openai_api_version,
        )
        self.prompt_provider = prompt_provider or build_prompt_provider()
        self.observability_client = observability_client or build_observability_client()

    @property
    def enabled(self) -> bool:
        return settings.azure_openai_transaction_category_enabled

    @property
    def model_name(self) -> str | None:
        return self.chat_client.deployment

    def classify_rows(
        self,
        *,
        rows: list[TransactionCategoryAssistantDraft],
        categories: list[Category],
    ) -> list[TransactionCategoryAssistantSuggestion]:
        if not self.enabled or not rows or not categories:
            return []

        if not self.chat_client.is_configured:
            return []

        prompt_variables = self._build_prompt_variables(rows=rows, categories=categories)
        prompt = self.prompt_provider.get_chat_prompt(
            TRANSACTION_CATEGORY_ASSISTANT_PROMPT_NAME,
            label=settings.langfuse_prompt_label,
            variables=prompt_variables,
        )
        deployment = self.chat_client.deployment

        try:
            completion = self.chat_client.complete_json(messages=prompt.messages)
            try:
                parsed = TransactionCategoryAssistantResponse.model_validate(
                    json.loads(completion.message)
                )
            except (json.JSONDecodeError, ValidationError) as exc:
                self.observability_client.record_generation(
                    handle=None,
                    name="azure_openai_transaction_category_generation",
                    model=deployment,
                    prompt=prompt,
                    input_payload={
                        "rows": prompt_variables["row_payload"],
                        "categories": prompt_variables["category_payload"],
                    },
                    output_payload={"raw_message": completion.message},
                    metadata={
                        "deployment": deployment,
                        "api_version": self.chat_client.api_version,
                        "prompt_source": prompt.source,
                        "prompt_version": prompt.version,
                        "latency_ms": completion.latency_ms,
                        "validation_error": str(exc),
                    },
                    status_message="Invalid classifier response payload",
                    level="WARNING",
                )
                return []
            self.observability_client.record_generation(
                handle=None,
                name="azure_openai_transaction_category_generation",
                model=deployment,
                prompt=prompt,
                input_payload={
                    "rows": prompt_variables["row_payload"],
                    "categories": prompt_variables["category_payload"],
                },
                output_payload={
                    "suggestions": [
                        suggestion.model_dump(mode="json") for suggestion in parsed.suggestions
                    ],
                    "raw_message": completion.message,
                },
                usage=completion.usage,
                cost=completion.cost,
                metadata={
                    "deployment": deployment,
                    "api_version": self.chat_client.api_version,
                    "prompt_source": prompt.source,
                    "prompt_version": prompt.version,
                    "latency_ms": completion.latency_ms,
                },
            )
            return parsed.suggestions
        except Exception as exc:
            self.observability_client.record_generation(
                handle=None,
                name="azure_openai_transaction_category_generation",
                model=deployment,
                prompt=prompt,
                input_payload={
                    "rows": prompt_variables["row_payload"],
                    "categories": prompt_variables["category_payload"],
                },
                output_payload=None,
                metadata={
                    "deployment": deployment,
                    "api_version": self.chat_client.api_version,
                    "prompt_source": prompt.source,
                    "prompt_version": prompt.version,
                    "latency_ms": None,
                },
                status_message=str(exc),
                level="ERROR",
            )
            raise

    def _build_prompt_variables(
        self,
        *,
        rows: list[TransactionCategoryAssistantDraft],
        categories: list[Category],
    ) -> dict[str, Any]:
        category_payload = [
            {
                "id": str(category.id),
                "name": category.name,
                "type": category.type.value,
            }
            for category in categories
        ]
        row_payload = [row.model_dump(mode="json") for row in rows]
        return build_category_classifier_variables(
            category_payload=category_payload,
            row_payload=row_payload,
        )
