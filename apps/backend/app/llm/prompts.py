from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.llm.eval_defs import (
    MONTHLY_INSIGHT_RECAP_PROMPT_NAME,
    PDF_TRANSACTION_PARSER_PROMPT_NAME,
    SLACK_DOCS_QA_PROMPT_NAME,
    TRANSACTION_CATEGORY_ASSISTANT_PROMPT_NAME,
)
from app.llm.types import ChatMessage, PromptDefinition

PROMPT_CATALOG_PATH = Path(__file__).with_name("catalog") / "prompts.yaml"
EXPECTED_PROMPT_NAMES = {
    MONTHLY_INSIGHT_RECAP_PROMPT_NAME,
    PDF_TRANSACTION_PARSER_PROMPT_NAME,
    SLACK_DOCS_QA_PROMPT_NAME,
    TRANSACTION_CATEGORY_ASSISTANT_PROMPT_NAME,
}


def _validate_messages(raw_messages: Any, *, prompt_name: str) -> tuple[ChatMessage, ...]:
    if not isinstance(raw_messages, list) or not raw_messages:
        raise ValueError(f"Prompt '{prompt_name}' must define at least one message")

    normalized_messages: list[ChatMessage] = []
    for index, raw_message in enumerate(raw_messages):
        if not isinstance(raw_message, dict):
            raise ValueError(f"Prompt '{prompt_name}' message #{index} must be a mapping")
        role = raw_message.get("role")
        content = raw_message.get("content")
        if not isinstance(role, str) or not role:
            raise ValueError(f"Prompt '{prompt_name}' message #{index} is missing a role")
        if not isinstance(content, str):
            raise ValueError(f"Prompt '{prompt_name}' message #{index} is missing content")
        normalized_messages.append({"role": role, "content": content})

    return tuple(normalized_messages)


@lru_cache(maxsize=1)
def _load_prompt_definitions() -> dict[str, PromptDefinition]:
    payload = yaml.safe_load(PROMPT_CATALOG_PATH.read_text(encoding="utf-8"))
    prompts = payload.get("prompts") if isinstance(payload, dict) else None
    if not isinstance(prompts, list):
        raise ValueError("Prompt catalog is missing a top-level 'prompts' list")

    definitions: dict[str, PromptDefinition] = {}
    for raw_prompt in prompts:
        if not isinstance(raw_prompt, dict):
            raise ValueError("Each prompt entry must be a mapping")
        name = raw_prompt.get("name")
        description = raw_prompt.get("description")
        labels = raw_prompt.get("labels")
        if not isinstance(name, str) or not name:
            raise ValueError("Each prompt entry must include a non-empty name")
        if not isinstance(description, str):
            raise ValueError(f"Prompt '{name}' must include a description")
        if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
            raise ValueError(f"Prompt '{name}' must include a string labels list")
        definitions[name] = PromptDefinition(
            name=name,
            description=description,
            labels=tuple(labels),
            messages=_validate_messages(raw_prompt.get("messages"), prompt_name=name),
        )

    missing_prompts = EXPECTED_PROMPT_NAMES - definitions.keys()
    if missing_prompts:
        missing = ", ".join(sorted(missing_prompts))
        raise ValueError(f"Prompt catalog is missing expected prompts: {missing}")

    return definitions


PROMPT_DEFINITIONS = _load_prompt_definitions()


def get_prompt_definition(name: str) -> PromptDefinition:
    return PROMPT_DEFINITIONS[name]
