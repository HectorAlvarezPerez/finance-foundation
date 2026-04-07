from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.llm.azure_chat import AzureChatCompletionClient
from app.llm.eval_defs import MONTHLY_INSIGHT_RECAP_PROMPT_NAME
from app.llm.prompt_variables import build_monthly_recap_variables
from app.llm.types import FlowHandle, LlmObservabilityClient, PromptProvider


class MonthlyRecapNarrativeStory(BaseModel):
    id: str
    headline: str = Field(min_length=1, max_length=160)
    subheadline: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1, max_length=320)


class MonthlyRecapNarrativeResponse(BaseModel):
    stories: list[MonthlyRecapNarrativeStory] = Field(default_factory=list)


class AzureOpenAIMonthlyRecapService:
    def __init__(
        self,
        *,
        prompt_provider: PromptProvider,
        observability_client: LlmObservabilityClient,
        chat_client: AzureChatCompletionClient | None = None,
    ) -> None:
        self.chat_client = chat_client or AzureChatCompletionClient(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_monthly_recap_deployment,
            api_version=settings.azure_openai_api_version,
        )
        self.prompt_provider = prompt_provider
        self.observability_client = observability_client

    @property
    def enabled(self) -> bool:
        return settings.azure_openai_monthly_recap_enabled

    @property
    def model_name(self) -> str | None:
        return self.chat_client.deployment

    def generate_story_copy(
        self,
        *,
        month_label: str,
        signals_payload: dict[str, Any],
        stories_payload: list[dict[str, Any]],
        handle: FlowHandle | None,
    ) -> dict[str, MonthlyRecapNarrativeStory] | None:
        if not self.enabled or not self.chat_client.is_configured or not stories_payload:
            return None

        prompt_variables = build_monthly_recap_variables(
            month_label=month_label,
            signals_payload=signals_payload,
            stories_payload=stories_payload,
        )
        prompt = self.prompt_provider.get_chat_prompt(
            MONTHLY_INSIGHT_RECAP_PROMPT_NAME,
            label=settings.langfuse_prompt_label,
            variables=prompt_variables,
        )
        deployment = self.chat_client.deployment

        try:
            completion = self.chat_client.complete_json(messages=prompt.messages, temperature=0.6)
            try:
                parsed = MonthlyRecapNarrativeResponse.model_validate(
                    json.loads(completion.message)
                )
            except (json.JSONDecodeError, ValidationError) as exc:
                self.observability_client.record_generation(
                    handle=handle,
                    name="azure_openai_monthly_recap_generation",
                    model=deployment,
                    prompt=prompt,
                    input_payload=prompt_variables,
                    output_payload={"raw_message": completion.message},
                    metadata={
                        "deployment": deployment,
                        "api_version": self.chat_client.api_version,
                        "prompt_source": prompt.source,
                        "prompt_version": prompt.version,
                        "latency_ms": completion.latency_ms,
                        "validation_error": str(exc),
                    },
                    status_message="Invalid monthly recap response payload",
                    level="WARNING",
                )
                return None

            self.observability_client.record_generation(
                handle=handle,
                name="azure_openai_monthly_recap_generation",
                model=deployment,
                prompt=prompt,
                input_payload=prompt_variables,
                output_payload={
                    "stories": [story.model_dump(mode="json") for story in parsed.stories],
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
            return {story.id: story for story in parsed.stories}
        except Exception as exc:
            self.observability_client.record_generation(
                handle=handle,
                name="azure_openai_monthly_recap_generation",
                model=deployment,
                prompt=prompt,
                input_payload=prompt_variables,
                output_payload=None,
                metadata={
                    "deployment": deployment,
                    "api_version": self.chat_client.api_version,
                    "prompt_source": prompt.source,
                    "prompt_version": prompt.version,
                },
                status_message=str(exc),
                level="ERROR",
            )
            return None
