import hashlib
import hmac
import time
from typing import Any, cast

from app.api.routes.slack import get_slack_docs_bot_service
from app.llm.observability import NoOpLlmObservabilityClient
from app.services.docs_qa_service import DocsQaAnswer, DocsQaService
from app.services.notion_docs_service import NotionDocumentMatch, NotionKnowledgeDocument
from app.services.slack_docs_bot_service import SlackDocsBotService


class StubNotionDocsService:
    def __init__(self, matches: list[NotionDocumentMatch]) -> None:
        self.matches = matches

    def search_documents(self, query: str, *, limit: int = 3) -> list[NotionDocumentMatch]:
        return self.matches[:limit]


def build_match(title: str, snippet: str) -> NotionDocumentMatch:
    return NotionDocumentMatch(
        document=NotionKnowledgeDocument(
            page_id=f"{title}-id",
            title=title,
            url=f"https://notion.so/{title}",
            category="Proceso",
            audience="Interno",
            surface="Transactions",
            status="Ready",
            source_type="Repo",
            source_ref="README.md",
            slack_ready=True,
            faq_seeds=None,
            content=snippet,
        ),
        score=12,
        snippet=snippet,
    )


def test_docs_qa_falls_back_to_extractive_answer_when_llm_is_not_configured() -> None:
    service = DocsQaService(
        notion_docs_service=cast(
            Any,
            StubNotionDocsService(
                [
                    build_match(
                        "Guía de transacciones e importación",
                        "El flujo soporta analyze, preview y commit para CSV, Excel y PDF.",
                    )
                ]
            ),
        ),
        observability_client=NoOpLlmObservabilityClient(),
    )

    answer = service.answer_question("¿Cómo importo un PDF?")

    assert answer.insufficient_context is False
    assert "Guía de transacciones e importación" in answer.answer
    assert answer.citations == ["Guía de transacciones e importación"]


def test_slack_signature_verification_matches_slack_scheme() -> None:
    body = b'{"type":"url_verification","challenge":"abc"}'
    timestamp = str(int(time.time()))
    secret = "super-secret"
    signature = (
        "v0="
        + hmac.new(
            secret.encode("utf-8"),
            f"v0:{timestamp}:{body.decode('utf-8')}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )

    service = SlackDocsBotService(
        docs_qa_service=None,
        observability_client=NoOpLlmObservabilityClient(),
        signing_secret=secret,
        bot_token="xoxb-test",
    )

    assert service.verify_request(body=body, timestamp=timestamp, signature=signature) is True


def test_process_event_posts_reply_for_app_mentions() -> None:
    posted: list[dict[str, str | None]] = []

    class StubDocsQaService:
        def answer_question(self, question: str, *, handle=None) -> DocsQaAnswer:
            return DocsQaAnswer(
                answer=f"Respuesta para: {question}",
                insufficient_context=False,
                citations=["Arquitectura técnica y autenticación"],
                matches=[],
            )

    service = SlackDocsBotService(
        docs_qa_service=cast(Any, StubDocsQaService()),
        observability_client=NoOpLlmObservabilityClient(),
        bot_token="xoxb-test",
        signing_secret="secret",
        bot_user_id="U_BOT",
    )

    service._post_message = lambda *, channel, text, thread_ts: posted.append(  # type: ignore[method-assign]
        {"channel": channel, "text": text, "thread_ts": thread_ts}
    )

    service.process_event(
        {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "channel": "C123",
                "user": "U123",
                "text": "<@U_BOT> como funciona auth",
                "ts": "123.456",
            },
        }
    )

    assert len(posted) == 1
    assert posted[0]["channel"] == "C123"
    assert "Respuesta para: como funciona auth" in str(posted[0]["text"])
    assert posted[0]["thread_ts"] == "123.456"


def test_slack_events_route_returns_challenge(client) -> None:
    class StubSlackBotService:
        def verify_request(self, *, body, timestamp, signature) -> bool:
            return True

        def handle_event_payload(self, payload):
            return {"challenge": payload["challenge"]}

        def process_event(self, payload) -> None:
            raise AssertionError("process_event should not run for url verification")

    app = client.app
    app.dependency_overrides[get_slack_docs_bot_service] = lambda: StubSlackBotService()
    try:
        response = client.post(
            "/api/v1/slack/events",
            headers={
                "X-Slack-Request-Timestamp": "1710000000",
                "X-Slack-Signature": "v0=test",
            },
            json={"type": "url_verification", "challenge": "abc123"},
        )
    finally:
        app.dependency_overrides.pop(get_slack_docs_bot_service, None)

    assert response.status_code == 200
    assert response.json() == {"challenge": "abc123"}
