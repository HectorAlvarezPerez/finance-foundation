from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.llm.azure_chat import AzureChatCompletionClient
from app.llm.eval_defs import SLACK_DOCS_QA_PROMPT_NAME
from app.llm.runtime import build_llm_runtime
from app.llm.types import FlowHandle, LlmObservabilityClient, PromptProvider
from app.services.notion_docs_service import NotionDocsService, NotionDocumentMatch


@dataclass(frozen=True)
class DocsQaAnswer:
    answer: str
    insufficient_context: bool
    citations: list[str]
    matches: list[NotionDocumentMatch]


class DocsQaResponse(BaseModel):
    answer: str = Field(min_length=1, max_length=1200)
    insufficient_context: bool = False
    citations: list[str] = Field(default_factory=list, max_length=3)


class NotionSearchService(Protocol):
    def search_documents(self, query: str, *, limit: int = 3) -> list[NotionDocumentMatch]: ...


class DocsQaService:
    def __init__(
        self,
        *,
        notion_docs_service: NotionSearchService | None = None,
        prompt_provider: PromptProvider | None = None,
        observability_client: LlmObservabilityClient | None = None,
        chat_client: AzureChatCompletionClient | None = None,
    ) -> None:
        runtime = build_llm_runtime()
        self.notion_docs_service = notion_docs_service or NotionDocsService()
        self.prompt_provider = prompt_provider or runtime.prompt_provider
        self.observability_client = observability_client or runtime.observability_client
        self.chat_client = chat_client or AzureChatCompletionClient(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_docs_qa_deployment,
            api_version=settings.azure_openai_api_version,
        )

    def answer_question(self, question: str, *, handle: FlowHandle | None = None) -> DocsQaAnswer:
        matches = self.notion_docs_service.search_documents(question, limit=3)
        if not matches:
            return DocsQaAnswer(
                answer=(
                    "No encuentro documentación suficiente en la base de Notion para responder "
                    "esa pregunta con seguridad."
                ),
                insufficient_context=True,
                citations=[],
                matches=[],
            )

        if not self.chat_client.is_configured:
            return self._build_extract_answer(question, matches)

        sources_payload = [
            {
                "title": match.document.title,
                "category": match.document.category,
                "surface": match.document.surface,
                "snippet": match.snippet,
                "url": match.document.url,
            }
            for match in matches
        ]
        prompt_variables = {
            "question": question.strip(),
            "sources_payload": json.dumps(sources_payload, ensure_ascii=False, indent=2),
        }
        prompt = self.prompt_provider.get_chat_prompt(
            SLACK_DOCS_QA_PROMPT_NAME,
            label=settings.langfuse_prompt_label,
            variables=prompt_variables,
        )
        deployment = self.chat_client.deployment

        try:
            completion = self.chat_client.complete_json(messages=prompt.messages, temperature=0.2)
            parsed = DocsQaResponse.model_validate(json.loads(completion.message))
            filtered_citations = self._filter_citations(parsed.citations, matches)
            answer = DocsQaAnswer(
                answer=parsed.answer.strip(),
                insufficient_context=parsed.insufficient_context,
                citations=filtered_citations,
                matches=matches,
            )
            self.observability_client.record_generation(
                handle=handle,
                name="slack_docs_qa_generation",
                model=deployment,
                prompt=prompt,
                input_payload={
                    "question": question,
                    "source_titles": [match.document.title for match in matches],
                },
                output_payload={
                    "answer": answer.answer,
                    "insufficient_context": answer.insufficient_context,
                    "citations": answer.citations,
                },
                usage=completion.usage,
                cost=completion.cost,
                metadata={
                    "deployment": deployment,
                    "api_version": self.chat_client.api_version,
                    "prompt_source": prompt.source,
                    "prompt_version": prompt.version,
                    "latency_ms": completion.latency_ms,
                },
            )
            return answer
        except (json.JSONDecodeError, ValidationError, Exception) as exc:
            self.observability_client.record_generation(
                handle=handle,
                name="slack_docs_qa_generation",
                model=deployment,
                prompt=prompt,
                input_payload={
                    "question": question,
                    "source_titles": [match.document.title for match in matches],
                },
                output_payload=None,
                metadata={
                    "deployment": deployment,
                    "api_version": self.chat_client.api_version,
                    "prompt_source": prompt.source,
                    "prompt_version": prompt.version,
                },
                status_message=str(exc),
                level="WARNING",
            )
            return self._build_extract_answer(question, matches)

    def _build_extract_answer(
        self,
        question: str,
        matches: list[NotionDocumentMatch],
    ) -> DocsQaAnswer:
        top = matches[0]
        citations = [match.document.title for match in matches[:3]]
        answer = (
            f"He encontrado documentación relacionada con “{question.strip()}” en "
            f"**{top.document.title}**. "
            f"{top.snippet or 'La base describe el flujo y sus detalles técnicos.'}"
        )
        return DocsQaAnswer(
            answer=answer,
            insufficient_context=False,
            citations=citations,
            matches=matches,
        )

    def _filter_citations(
        self,
        citations: list[str],
        matches: list[NotionDocumentMatch],
    ) -> list[str]:
        allowed = {match.document.title for match in matches}
        filtered = [citation for citation in citations if citation in allowed]
        if filtered:
            return filtered[:3]
        return [match.document.title for match in matches[:3]]
