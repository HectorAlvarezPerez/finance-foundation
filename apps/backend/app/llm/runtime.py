from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.llm.observability import LangfuseObservabilityClient, NoOpLlmObservabilityClient
from app.llm.prompt_provider import LangfusePromptProvider, NoOpPromptProvider
from app.llm.types import LlmObservabilityClient, PromptProvider


@dataclass(frozen=True)
class LlmRuntime:
    prompt_provider: PromptProvider
    observability_client: LlmObservabilityClient


def build_prompt_provider() -> PromptProvider:
    if settings.langfuse_enabled_configured:
        return LangfusePromptProvider(settings)
    return NoOpPromptProvider()


def build_observability_client() -> LlmObservabilityClient:
    if settings.langfuse_enabled_configured:
        return LangfuseObservabilityClient(settings)
    return NoOpLlmObservabilityClient()


def build_llm_runtime() -> LlmRuntime:
    return LlmRuntime(
        prompt_provider=build_prompt_provider(),
        observability_client=build_observability_client(),
    )
