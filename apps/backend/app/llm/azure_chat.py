from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.llm.types import ChatMessage


@dataclass(frozen=True)
class ChatCompletionResult:
    payload: dict[str, Any]
    message: str
    latency_ms: float
    usage: dict[str, int] | None
    cost: dict[str, float] | None


class AzureChatCompletionClient:
    def __init__(
        self,
        *,
        endpoint: str | None,
        api_key: str | None,
        deployment: str | None,
        api_version: str,
        timeout_seconds: float = 45.0,
    ) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment = deployment
        self.api_version = api_version
        self.timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        return (
            self.endpoint is not None and self.api_key is not None and self.deployment is not None
        )

    def complete_json(
        self,
        *,
        messages: list[ChatMessage],
        temperature: int | float = 0,
    ) -> ChatCompletionResult:
        if not self.is_configured:
            raise RuntimeError("Azure chat completion client is not configured")

        assert self.endpoint is not None
        assert self.api_key is not None
        assert self.deployment is not None

        url = (
            f"{self.endpoint.rstrip('/')}/openai/deployments/{self.deployment}/chat/completions"
            f"?api-version={self.api_version}"
        )
        request_payload = {
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        started_at = time.perf_counter()
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                url,
                headers={
                    "api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json=request_payload,
            )
            response.raise_for_status()

        payload = response.json()
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        message = str(payload["choices"][0]["message"]["content"])
        usage, cost = self._extract_usage_and_cost(payload)

        return ChatCompletionResult(
            payload=payload,
            message=message,
            latency_ms=latency_ms,
            usage=usage,
            cost=cost,
        )

    def _extract_usage_and_cost(
        self,
        payload: dict[str, Any],
    ) -> tuple[dict[str, int] | None, dict[str, float] | None]:
        raw_usage = payload.get("usage")
        usage_details: dict[str, int] | None = None
        if isinstance(raw_usage, dict):
            usage_details = {
                key: int(value) for key, value in raw_usage.items() if isinstance(value, int)
            } or None

        raw_cost = payload.get("cost")
        cost_details: dict[str, float] | None = None
        if isinstance(raw_cost, dict):
            cost_details = {
                key: float(value)
                for key, value in raw_cost.items()
                if isinstance(value, int | float)
            } or None

        return usage_details, cost_details
