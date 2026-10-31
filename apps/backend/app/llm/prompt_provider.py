from __future__ import annotations

import logging
from typing import Any, cast

from langfuse import Langfuse

from app.core.config import Settings
from app.llm.prompts import get_prompt_definition
from app.llm.types import PromptProvider, ResolvedPrompt, render_prompt_messages

logger = logging.getLogger(__name__)


class NoOpPromptProvider(PromptProvider):
    def get_chat_prompt(
        self,
        name: str,
        *,
        label: str,
        variables: dict[str, Any],
    ) -> ResolvedPrompt:
        definition = get_prompt_definition(name)
        return ResolvedPrompt(
            name=name,
            label=label,
            version=None,
            source="local_fallback",
            messages=render_prompt_messages(definition.messages, variables),
        )


class LangfusePromptProvider(PromptProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        self.fallback_provider = NoOpPromptProvider()

    def get_chat_prompt(
        self,
        name: str,
        *,
        label: str,
        variables: dict[str, Any],
    ) -> ResolvedPrompt:
        definition = get_prompt_definition(name)
        fallback_messages = render_prompt_messages(definition.messages, variables)
        try:
            prompt_client = self.client.get_prompt(
                name,
                label=label,
                type="chat",
                fallback=list(definition.messages),
            )
            compiled = prompt_client.compile(**variables)
            return ResolvedPrompt(
                name=name,
                label=label,
                version=getattr(prompt_client, "version", None),
                source="langfuse",
                messages=[
                    {
                        "role": str(cast(dict[str, Any], message).get("role", "user")),
                        "content": str(cast(dict[str, Any], message).get("content", "")),
                    }
                    for message in compiled
                ],
                prompt_client=prompt_client,
            )
        except Exception:
            logger.exception("Failed to fetch Langfuse prompt %s, using local fallback", name)
            return ResolvedPrompt(
                name=name,
                label=label,
                version=None,
                source="local_fallback",
                messages=fallback_messages,
            )
