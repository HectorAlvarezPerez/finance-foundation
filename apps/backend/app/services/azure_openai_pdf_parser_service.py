from __future__ import annotations

import json

from app.core.config import settings
from app.llm.azure_chat import AzureChatCompletionClient
from app.llm.eval_defs import PDF_TRANSACTION_PARSER_PROMPT_NAME
from app.llm.prompt_variables import build_pdf_parser_variables
from app.llm.runtime import build_observability_client, build_prompt_provider
from app.llm.types import LlmObservabilityClient, PromptProvider
from app.schemas.transactions import PdfParsedTransactionsResponse


class AzureOpenAIPdfParserService:
    def __init__(
        self,
        *,
        chat_client: AzureChatCompletionClient | None = None,
        prompt_provider: PromptProvider | None = None,
        observability_client: LlmObservabilityClient | None = None,
    ) -> None:
        self.chat_client = chat_client or AzureChatCompletionClient(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_pdf_parser_deployment,
            api_version=settings.azure_openai_api_version,
        )
        self.prompt_provider = prompt_provider or build_prompt_provider()
        self.observability_client = observability_client or build_observability_client()

    @property
    def enabled(self) -> bool:
        return settings.azure_openai_pdf_parser_enabled

    def parse_transactions(
        self,
        *,
        structured_text: str,
        tables_markdown: str,
    ) -> list[dict[str, str]]:
        if not self.enabled:
            return []

        if not self.chat_client.is_configured:
            return []

        prompt_variables = build_pdf_parser_variables(
            structured_text=structured_text,
            tables_markdown=tables_markdown,
        )
        prompt = self.prompt_provider.get_chat_prompt(
            PDF_TRANSACTION_PARSER_PROMPT_NAME,
            label=settings.langfuse_prompt_label,
            variables=prompt_variables,
        )
        deployment = self.chat_client.deployment

        try:
            completion = self.chat_client.complete_json(messages=prompt.messages)
            parsed = PdfParsedTransactionsResponse.model_validate(json.loads(completion.message))
            normalized_transactions = [
                {
                    "Fecha": item.date.strip(),
                    "Descripción": item.description.strip(),
                    "Importe": item.amount.strip(),
                }
                for item in parsed.transactions
            ]
            final_rows = [row for row in normalized_transactions if any(row.values())]
            self.observability_client.record_generation(
                handle=None,
                name="azure_openai_pdf_parser_generation",
                model=deployment,
                prompt=prompt,
                input_payload={
                    "structured_text": structured_text,
                    "tables_markdown": tables_markdown,
                },
                output_payload={
                    "transactions": final_rows,
                    "raw_message": completion.message,
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
            return final_rows
        except Exception as exc:
            self.observability_client.record_generation(
                handle=None,
                name="azure_openai_pdf_parser_generation",
                model=deployment,
                prompt=prompt,
                input_payload={
                    "structured_text": structured_text,
                    "tables_markdown": tables_markdown,
                },
                output_payload=None,
                metadata={
                    "deployment": deployment,
                    "api_version": self.chat_client.api_version,
                    "prompt_source": prompt.source,
                    "prompt_version": prompt.version,
                    "latency_ms": None,
                },
                status_message=str(exc),
                level="ERROR",
            )
            raise
