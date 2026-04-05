from __future__ import annotations

import logging
from typing import Any, cast

from langfuse import Langfuse

from app.core.config import Settings
from app.llm.types import FlowHandle, LlmObservabilityClient, ResolvedPrompt

logger = logging.getLogger(__name__)


class NoOpLlmObservabilityClient(LlmObservabilityClient):
    def start_flow(
        self,
        name: str,
        *,
        input_payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> FlowHandle:
        return FlowHandle(
            name=name,
            metadata=metadata or {},
            input_payload=input_payload,
        )

    def end_flow(
        self,
        handle: FlowHandle,
        *,
        output_payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        status_message: str | None = None,
        level: str | None = None,
    ) -> None:
        return None

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
    ) -> None:
        return None

    def record_score(
        self,
        *,
        handle: FlowHandle | None,
        name: str,
        value: float,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        return None

    def flush(self) -> None:
        return None


class LangfuseObservabilityClient(LlmObservabilityClient):
    def __init__(self, settings: Settings) -> None:
        self.client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )

    def start_flow(
        self,
        name: str,
        *,
        input_payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> FlowHandle:
        merged_metadata = metadata or {}
        try:
            context_manager = self.client.start_as_current_observation(
                name=name,
                as_type="span",
                input=input_payload,
                metadata=merged_metadata,
                end_on_exit=False,
            )
            span = context_manager.__enter__()
            return FlowHandle(
                name=name,
                metadata=merged_metadata,
                input_payload=input_payload,
                span=span,
                context_manager=context_manager,
            )
        except Exception:
            logger.exception("Failed to start Langfuse flow %s", name)
            return FlowHandle(name=name, metadata=merged_metadata, input_payload=input_payload)

    def end_flow(
        self,
        handle: FlowHandle,
        *,
        output_payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        status_message: str | None = None,
        level: str | None = None,
    ) -> None:
        if handle.span is None or handle.context_manager is None:
            return

        try:
            merged_metadata = dict(handle.metadata)
            if metadata:
                merged_metadata.update(metadata)
            handle.span.update(
                output=output_payload,
                metadata=merged_metadata,
                status_message=status_message,
                level=level,
            )
        except Exception:
            logger.exception("Failed to update Langfuse flow %s", handle.name)
        finally:
            try:
                handle.span.end()
                handle.context_manager.__exit__(None, None, None)
            except Exception:
                logger.exception("Failed to close Langfuse flow %s", handle.name)

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
    ) -> None:
        trace_context: dict[str, str] | None = None
        if handle and handle.trace_id and handle.observation_id:
            trace_context = {
                "trace_id": handle.trace_id,
                "parent_observation_id": handle.observation_id,
            }

        try:
            with self.client.start_as_current_observation(
                trace_context=cast(Any, trace_context),
                name=name,
                as_type="generation",
                input=input_payload,
                output=output_payload,
                metadata=metadata,
                model=model,
                usage_details=usage,
                cost_details=cost,
                prompt=prompt.prompt_client,
                status_message=status_message,
                level=cast(Any, level),
            ):
                return None
        except Exception:
            logger.exception("Failed to record Langfuse generation %s", name)

    def record_score(
        self,
        *,
        handle: FlowHandle | None,
        name: str,
        value: float,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if handle is None or handle.trace_id is None:
            return
        try:
            self.client.create_score(
                trace_id=handle.trace_id,
                observation_id=handle.observation_id,
                name=name,
                value=value,
                comment=comment,
                metadata=metadata,
            )
        except Exception:
            logger.exception("Failed to record Langfuse score %s", name)

    def flush(self) -> None:
        try:
            self.client.flush()
        except Exception:
            logger.exception("Failed to flush Langfuse client")
