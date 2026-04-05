from __future__ import annotations

import json

import httpx

from app.core.config import settings
from app.models.category import Category
from app.schemas.transactions import (
    TransactionCategoryAssistantDraft,
    TransactionCategoryAssistantResponse,
    TransactionCategoryAssistantSuggestion,
)


class AzureOpenAITransactionCategoryService:
    def __init__(self) -> None:
        self.endpoint = settings.azure_openai_endpoint
        self.api_key = settings.azure_openai_api_key
        self.deployment = settings.azure_openai_transaction_category_deployment
        self.api_version = settings.azure_openai_api_version

    @property
    def enabled(self) -> bool:
        return settings.azure_openai_transaction_category_enabled

    @property
    def model_name(self) -> str | None:
        return self.deployment

    def classify_rows(
        self,
        *,
        rows: list[TransactionCategoryAssistantDraft],
        categories: list[Category],
    ) -> list[TransactionCategoryAssistantSuggestion]:
        if not self.enabled or not rows or not categories:
            return []

        endpoint = self.endpoint
        api_key = self.api_key
        deployment = self.deployment
        if endpoint is None or api_key is None or deployment is None:
            return []

        prompt = self._build_prompt(rows=rows, categories=categories)
        url = (
            f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={self.api_version}"
        )

        with httpx.Client(timeout=45.0) as client:
            response = client.post(
                url,
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an expert financial transaction classifier. "
                                "Your job is to assign imported bank and card transactions to the "
                                "most appropriate existing user category when there is enough "
                                "evidence. You are conservative, consistent, and good at "
                                "recognizing merchant intent across noisy labels, abbreviations, "
                                "multiple languages, and banking-style descriptors. "
                                "Only choose from the provided categories and return valid JSON."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()

        payload = response.json()
        message = payload["choices"][0]["message"]["content"]
        parsed = TransactionCategoryAssistantResponse.model_validate(json.loads(message))
        return parsed.suggestions

    def _build_prompt(
        self,
        *,
        rows: list[TransactionCategoryAssistantDraft],
        categories: list[Category],
    ) -> str:
        category_payload = [
            {
                "id": str(category.id),
                "name": category.name,
                "type": category.type.value,
            }
            for category in categories
        ]
        row_payload = [row.model_dump(mode="json") for row in rows]

        return f"""
Suggest categories for the imported transactions below.

Rules:
- Return a JSON object with a single key called "suggestions".
- Each suggestion must include: source_row_number, category_id, confidence.
- category_id must be one of the provided category IDs or null.
- confidence must be a conservative number between 0 and 1.
- If you are not clearly confident enough, return null for category_id.
- Do not invent categories.
- Prefer expense categories for negative amounts and income categories for positive amounts.
- Transfer categories are allowed only when the description clearly looks like a transfer.
- Use the transaction description as the main signal and use notes as supporting context.
- Infer merchant intent from natural language, abbreviations,
  acronyms, and multilingual labels when reasonable.
- Match the transaction to the closest user category conceptually,
  not only by literal keyword overlap.
- If several categories could fit and none is clearly better, return null.
- Be especially good at common personal finance categories such as
  groceries, transport, housing, leisure, health, sports,
  subscriptions, transfers, salary, and savings.

Available categories:
{json.dumps(category_payload, ensure_ascii=False)}

Transactions:
{json.dumps(row_payload, ensure_ascii=False)}
""".strip()
