from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Protocol

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.llm.runtime import build_llm_runtime
from app.llm.types import LlmObservabilityClient
from app.services.docs_qa_service import DocsQaAnswer, DocsQaService
from app.services.notion_docs_service import NotionDocumentMatch

SLACK_SIGNATURE_VERSION = "v0"
SLACK_REPLY_FOOTER = (
    "_Fuente: base documental demo de Finance Foundation en Notion. "
    "No responde sobre código no documentado._"
)


class DocsQuestionAnswerer(Protocol):
    notion_docs_service: Any

    def answer_question(self, question: str, *, handle: Any = None) -> DocsQaAnswer: ...


class SlackDocsBotService:
    def __init__(
        self,
        *,
        docs_qa_service: DocsQuestionAnswerer | None = None,
        observability_client: LlmObservabilityClient | None = None,
        bot_token: str | None = None,
        signing_secret: str | None = None,
        bot_user_id: str | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        runtime = build_llm_runtime()
        self.docs_qa_service = docs_qa_service or DocsQaService()
        self.observability_client = observability_client or runtime.observability_client
        self.bot_token = bot_token or settings.slack_bot_token
        self.signing_secret = signing_secret or settings.slack_signing_secret
        self.bot_user_id = bot_user_id or settings.slack_bot_user_id
        self.timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        notion_configured = getattr(
            self.docs_qa_service.notion_docs_service,
            "is_configured",
            False,
        )
        return bool(self.bot_token and self.signing_secret and notion_configured)

    def verify_request(self, *, body: bytes, timestamp: str | None, signature: str | None) -> bool:
        if not self.signing_secret or not timestamp or not signature:
            return False

        try:
            request_time = int(timestamp)
        except ValueError:
            return False

        if abs(time.time() - request_time) > 60 * 5:
            return False

        basestring = f"{SLACK_SIGNATURE_VERSION}:{timestamp}:{body.decode('utf-8')}"
        computed = hmac.new(
            self.signing_secret.encode("utf-8"),
            basestring.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        expected = f"{SLACK_SIGNATURE_VERSION}={computed}"
        return hmac.compare_digest(expected, signature)

    def handle_event_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge", "")}
        return {"ok": True}

    def process_event(self, payload: dict[str, Any]) -> None:
        if not self.bot_token:
            return

        if payload.get("type") != "event_callback":
            return

        event = payload.get("event")
        if not isinstance(event, dict):
            return
        if self._should_ignore_event(event):
            return

        question = self._extract_question(event)
        if not question:
            return

        channel = event.get("channel")
        if not isinstance(channel, str) or not channel:
            return

        thread_ts = str(event.get("thread_ts") or event.get("ts") or "")
        flow = self.observability_client.start_flow(
            "slack_docs_bot_answer",
            input_payload={
                "channel": channel,
                "question": question,
                "event_type": event.get("type"),
            },
            metadata={
                "channel": channel,
                "event_type": str(event.get("type", "")),
                "user": str(event.get("user", "")),
            },
        )

        try:
            answer = self.docs_qa_service.answer_question(question, handle=flow)
            text = self._format_reply(answer.answer, answer.citations, answer.matches)
            self._post_message(channel=channel, text=text, thread_ts=thread_ts or None)
            self.observability_client.end_flow(
                flow,
                output_payload={
                    "citations": answer.citations,
                    "insufficient_context": answer.insufficient_context,
                },
                metadata={"thread_ts": thread_ts or None},
            )
        except Exception as exc:
            self.observability_client.end_flow(
                flow,
                output_payload=None,
                status_message=str(exc),
                level="ERROR",
            )

    def require_configured(self) -> None:
        if self.is_configured:
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Slack docs bot is not configured",
        )

    def _should_ignore_event(self, event: dict[str, Any]) -> bool:
        if event.get("bot_id"):
            return True
        subtype = event.get("subtype")
        if isinstance(subtype, str) and subtype:
            return True

        event_type = event.get("type")
        if event_type == "app_mention":
            return False
        if event_type == "message" and event.get("channel_type") == "im":
            return False
        return True

    def _extract_question(self, event: dict[str, Any]) -> str:
        text = str(event.get("text", "")).strip()
        if not text:
            return ""
        if self.bot_user_id:
            text = text.replace(f"<@{self.bot_user_id}>", "").strip()
        return " ".join(text.split())

    def _format_reply(
        self,
        answer: str,
        citations: list[str],
        matches: list[NotionDocumentMatch],
    ) -> str:
        lines = [answer.strip()]
        if citations:
            lines.append("")
            lines.append("*Fuentes*")
            lines.extend(self._format_citation_lines(citations, matches))
        lines.append("")
        lines.append(SLACK_REPLY_FOOTER)
        return "\n".join(lines).strip()

    def _format_citation_lines(
        self,
        citations: list[str],
        matches: list[NotionDocumentMatch],
    ) -> list[str]:
        title_to_url = {
            match.document.title: match.document.url
            for match in matches
            if getattr(match.document, "url", "")
        }
        lines: list[str] = []
        for citation in citations:
            url = title_to_url.get(citation)
            if url:
                lines.append(f"- {citation}: {url}")
            else:
                lines.append(f"- {citation}")
        return lines

    def _post_message(self, *, channel: str, text: str, thread_ts: str | None) -> None:
        assert self.bot_token is not None
        payload: dict[str, Any] = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {self.bot_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
            if not bool(body.get("ok")):
                raise RuntimeError(str(body.get("error", "Slack API request failed")))
