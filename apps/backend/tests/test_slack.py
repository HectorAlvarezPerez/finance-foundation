import hashlib
import hmac
import json
import time
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, cast

import pytest

from app.api.routes.slack import get_slack_docs_bot_service
from app.main import app
from app.services.slack_docs_bot_service import SlackDocsBotService


@dataclass(frozen=True)
class FakeDocument:
    title: str
    url: str


@dataclass(frozen=True)
class FakeMatch:
    document: FakeDocument


@dataclass(frozen=True)
class FakeAnswer:
    answer: str
    insufficient_context: bool
    citations: list[str]
    matches: list[FakeMatch]


class FakeNotionDocsService:
    is_configured = True


class FakeDocsQaService:
    def __init__(self) -> None:
        self.notion_docs_service = FakeNotionDocsService()
        self.questions: list[str] = []

    def answer_question(self, question: str, *, handle=None) -> FakeAnswer:  # type: ignore[no-untyped-def]
        self.questions.append(question)
        return FakeAnswer(
            answer="Auth funciona con sesión de backend y puede exponer proveedores configurados.",
            insufficient_context=False,
            citations=["Arquitectura técnica y autenticación"],
            matches=[
                FakeMatch(
                    document=FakeDocument(
                        title="Arquitectura técnica y autenticación",
                        url="https://www.notion.so/demo-auth",
                    )
                )
            ],
        )


class FakeSlackDocsBotService(SlackDocsBotService):
    def __init__(self) -> None:
        super().__init__(
            docs_qa_service=cast(Any, FakeDocsQaService()),
            bot_token="xoxb-test",
            signing_secret="slack-secret",
            bot_user_id="U_BOT",
        )
        self.sent_messages: list[dict[str, str | None]] = []

    def _post_message(self, *, channel: str, text: str, thread_ts: str | None) -> None:
        self.sent_messages.append(
            {
                "channel": channel,
                "text": text,
                "thread_ts": thread_ts,
            }
        )


def _sign(body: bytes, *, secret: str, timestamp: int) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        f"v0:{timestamp}:{body.decode('utf-8')}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"v0={digest}"


@pytest.fixture
def slack_service() -> Generator[FakeSlackDocsBotService, None, None]:
    service = FakeSlackDocsBotService()
    app.dependency_overrides[get_slack_docs_bot_service] = lambda: service
    try:
        yield service
    finally:
        app.dependency_overrides.pop(get_slack_docs_bot_service, None)


def test_slack_url_verification_returns_challenge(client, slack_service) -> None:
    payload = {"type": "url_verification", "challenge": "abc123"}
    body = json.dumps(payload).encode("utf-8")
    timestamp = int(time.time())

    response = client.post(
        "/api/v1/slack/events",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Slack-Request-Timestamp": str(timestamp),
            "X-Slack-Signature": _sign(body, secret="slack-secret", timestamp=timestamp),
        },
    )

    assert response.status_code == 200
    assert response.json() == {"challenge": "abc123"}


def test_slack_app_mention_posts_thread_reply_with_source_links(client, slack_service) -> None:
    payload = {
        "type": "event_callback",
        "event": {
            "type": "app_mention",
            "user": "U123",
            "channel": "C123",
            "text": "<@U_BOT> como funciona auth?",
            "ts": "1710000000.000100",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    timestamp = int(time.time())

    response = client.post(
        "/api/v1/slack/events",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Slack-Request-Timestamp": str(timestamp),
            "X-Slack-Signature": _sign(body, secret="slack-secret", timestamp=timestamp),
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert slack_service.sent_messages == [
        {
            "channel": "C123",
            "text": (
                "Auth funciona con sesión de backend y puede exponer proveedores configurados.\n\n"
                "*Fuentes*\n"
                "- Arquitectura técnica y autenticación: https://www.notion.so/demo-auth\n\n"
                "_Fuente: base documental demo de Finance Foundation en Notion. "
                "No responde sobre código no documentado._"
            ),
            "thread_ts": "1710000000.000100",
        }
    ]


def test_slack_invalid_signature_returns_unauthorized(client, slack_service) -> None:
    payload = {"type": "url_verification", "challenge": "abc123"}
    body = json.dumps(payload).encode("utf-8")
    timestamp = int(time.time())

    response = client.post(
        "/api/v1/slack/events",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Slack-Request-Timestamp": str(timestamp),
            "X-Slack-Signature": "v0=invalid",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Slack signature"
