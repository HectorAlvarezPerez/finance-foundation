from __future__ import annotations

from dataclasses import dataclass
from string import Template
from typing import Any, Literal, Protocol, TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


@dataclass(frozen=True)
class PromptDefinition:
    name: str
    description: str
    labels: tuple[str, ...]
    messages: tuple[ChatMessage, ...]


@dataclass(frozen=True)
class ResolvedPrompt:
    name: str
    label: str
    version: int | None
    source: Literal["langfuse", "local_fallback"]
    messages: list[ChatMessage]
    prompt_client: Any | None = None


@dataclass
class FlowHandle:
    name: str
    metadata: dict[str, Any]
    input_payload: dict[str, Any]
    span: Any | None = None
    context_manager: Any | None = None

    @property
    def observation_id(self) -> str | None:
        return getattr(self.span, "id", None)

    @property
    def trace_id(self) -> str | None:
        return getattr(self.span, "trace_id", None)


class PromptProvider(Protocol):
    def get_chat_prompt(
        self,
        name: str,
        *,
        label: str,
        variables: dict[str, Any],
    ) -> ResolvedPrompt: ...


class LlmObservabilityClient(Protocol):
    def start_flow(
        self,
        name: str,
        *,
        input_payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> FlowHandle: ...

    def end_flow(
        self,
        handle: FlowHandle,
        *,
        output_payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        status_message: str | None = None,
        level: str | None = None,
    ) -> None: ...

    def record_generation(
        self,
        *,
        handle: FlowHandle | None,
        name: str,
        model: str | None,
        prompt: ResolvedPrompt,
        input_payload: dict[str, Any] | None,
        output_payload: Any | None,
        usage: dict[str, int] | None = None,
        cost: dict[str, float] | None = None,
        metadata: dict[str, Any] | None = None,
        status_message: str | None = None,
        level: str | None = None,
    ) -> None: ...

    def record_score(
        self,
        *,
        handle: FlowHandle | None,
        name: str,
        value: float,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    def flush(self) -> None: ...


def render_template_string(template: str, variables: dict[str, Any]) -> str:
    prepared = {key: "" if value is None else str(value) for key, value in variables.items()}
    return Template(template).safe_substitute(prepared)


def render_prompt_messages(
    messages: tuple[ChatMessage, ...],
    variables: dict[str, Any],
) -> list[ChatMessage]:
    return [
        {
            "role": message["role"],
            "content": render_template_string(message["content"], variables),
        }
        for message in messages
    ]
