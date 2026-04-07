from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.llm.azure_chat import AzureChatCompletionClient
from app.llm.eval_defs import MONTHLY_INSIGHT_RECAP_PROMPT_NAME
from app.llm.prompt_variables import build_monthly_recap_variables
from app.llm.types import (
    ChatMessage,
    FlowHandle,
    LlmObservabilityClient,
    PromptProvider,
    ResolvedPrompt,
)

STRICT_RETRY_TEMPERATURE = 0


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
        expected_story_ids = [str(story["id"]) for story in stories_payload if story.get("id")]

        attempt_definitions: list[tuple[str, ResolvedPrompt, int | float]] = [
            ("default", prompt, 0.6),
            (
                "strict_retry",
                self._build_strict_retry_prompt(
                    prompt=prompt,
                    expected_story_ids=expected_story_ids,
                ),
                STRICT_RETRY_TEMPERATURE,
            ),
        ]

        attempt_errors: list[dict[str, Any]] = []
        last_completion_message: str | None = None
        last_usage: dict[str, int] | None = None
        last_cost: dict[str, float] | None = None
        last_latency_ms: float | None = None
        last_invalid_reason: str | None = None
        last_prompt: ResolvedPrompt = prompt

        try:
            for attempt_index, (attempt_mode, attempt_prompt, attempt_temperature) in enumerate(
                attempt_definitions,
                start=1,
            ):
                last_prompt = attempt_prompt
                try:
                    completion = self.chat_client.complete_json(
                        messages=attempt_prompt.messages,
                        temperature=attempt_temperature,
                    )
                except Exception as exc:
                    attempt_errors.append(
                        {
                            "attempt": attempt_index,
                            "attempt_mode": attempt_mode,
                            "error": str(exc),
                        }
                    )
                    last_invalid_reason = "llm_request_error"
                    continue

                last_completion_message = completion.message
                last_usage = completion.usage
                last_cost = completion.cost
                last_latency_ms = completion.latency_ms

                try:
                    parsed = MonthlyRecapNarrativeResponse.model_validate(
                        json.loads(completion.message)
                    )
                except (json.JSONDecodeError, ValidationError) as exc:
                    last_invalid_reason = "llm_invalid_payload"
                    attempt_errors.append(
                        {
                            "attempt": attempt_index,
                            "attempt_mode": attempt_mode,
                            "error": str(exc),
                            "invalid_reason": last_invalid_reason,
                        }
                    )
                    continue

                invalid_reason, missing_story_ids, unexpected_story_ids = self._validate_story_ids(
                    parsed=parsed,
                    expected_story_ids=expected_story_ids,
                )
                if invalid_reason is not None:
                    last_invalid_reason = invalid_reason
                    attempt_errors.append(
                        {
                            "attempt": attempt_index,
                            "attempt_mode": attempt_mode,
                            "invalid_reason": invalid_reason,
                            "missing_story_ids": missing_story_ids,
                            "unexpected_story_ids": unexpected_story_ids,
                            "returned_story_ids": [story.id for story in parsed.stories],
                        }
                    )
                    continue

                self.observability_client.record_generation(
                    handle=handle,
                    name="azure_openai_monthly_recap_generation",
                    model=deployment,
                    prompt=attempt_prompt,
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
                        "prompt_source": attempt_prompt.source,
                        "prompt_version": attempt_prompt.version,
                        "latency_ms": completion.latency_ms,
                        "attempt_count": attempt_index,
                        "attempt_mode": attempt_mode,
                        "retried": attempt_index > 1,
                    },
                )
                return {story.id: story for story in parsed.stories}

            self.observability_client.record_generation(
                handle=handle,
                name="azure_openai_monthly_recap_generation",
                model=deployment,
                prompt=last_prompt,
                input_payload=prompt_variables,
                output_payload={"raw_message": last_completion_message},
                usage=last_usage,
                cost=last_cost,
                metadata={
                    "deployment": deployment,
                    "api_version": self.chat_client.api_version,
                    "prompt_source": last_prompt.source,
                    "prompt_version": last_prompt.version,
                    "latency_ms": last_latency_ms,
                    "invalid_reason": last_invalid_reason or "llm_invalid_payload",
                    "expected_story_ids": expected_story_ids,
                    "attempt_count": len(attempt_definitions),
                    "attempt_errors": attempt_errors,
                },
                status_message="Invalid monthly recap response payload",
                level="WARNING",
            )
            return None
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

    def _build_strict_retry_prompt(
        self,
        *,
        prompt: ResolvedPrompt,
        expected_story_ids: list[str],
    ) -> ResolvedPrompt:
        strict_instruction = self._build_strict_retry_instruction(expected_story_ids)
        strict_messages: list[ChatMessage] = [*prompt.messages, strict_instruction]
        return ResolvedPrompt(
            name=prompt.name,
            label=prompt.label,
            version=prompt.version,
            source=prompt.source,
            messages=strict_messages,
            prompt_client=prompt.prompt_client,
        )

    def _build_strict_retry_instruction(self, expected_story_ids: list[str]) -> ChatMessage:
        expected_ids_json = json.dumps(expected_story_ids, ensure_ascii=False)
        return {
            "role": "user",
            "content": (
                "The previous output was invalid. Return ONLY a JSON object "
                'with the key "stories". '
                "The stories array must be non-empty and contain exactly one item per expected ID. "
                "Use these IDs exactly and in this exact order: "
                f"{expected_ids_json}. "
                "Each story object must include exactly: id, headline, subheadline, body. "
                "Do not add or remove stories and do not include extra keys."
            ),
        }

    def _validate_story_ids(
        self,
        *,
        parsed: MonthlyRecapNarrativeResponse,
        expected_story_ids: list[str],
    ) -> tuple[str | None, list[str], list[str]]:
        expected_story_id_set = set(expected_story_ids)
        returned_story_ids = [story.id for story in parsed.stories]
        returned_story_id_set = set(returned_story_ids)
        missing_story_ids = sorted(expected_story_id_set - returned_story_id_set)
        unexpected_story_ids = sorted(returned_story_id_set - expected_story_id_set)
        if len(parsed.stories) == 0:
            return "llm_empty_stories", missing_story_ids, unexpected_story_ids
        if missing_story_ids or unexpected_story_ids:
            return "llm_story_ids_mismatch", missing_story_ids, unexpected_story_ids
        return None, [], []
