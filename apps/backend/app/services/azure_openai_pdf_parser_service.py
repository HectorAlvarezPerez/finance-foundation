from __future__ import annotations

import json

import httpx

from app.core.config import settings
from app.schemas.transactions import PdfParsedTransactionsResponse


class AzureOpenAIPdfParserService:
    def __init__(self) -> None:
        self.endpoint = settings.azure_openai_endpoint
        self.api_key = settings.azure_openai_api_key
        self.deployment = settings.azure_openai_pdf_parser_deployment
        self.api_version = settings.azure_openai_api_version

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

        endpoint = self.endpoint
        api_key = self.api_key
        deployment = self.deployment
        if endpoint is None or api_key is None or deployment is None:
            return []

        prompt = self._build_prompt(
            structured_text=structured_text,
            tables_markdown=tables_markdown,
        )

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
                                "You extract bank transactions from OCR output. "
                                "Return only valid JSON."
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
        parsed = PdfParsedTransactionsResponse.model_validate(json.loads(message))
        normalized_transactions = [
            {
                "Fecha": item.date.strip(),
                "Descripción": item.description.strip(),
                "Importe": item.amount.strip(),
            }
            for item in parsed.transactions
        ]
        return [row for row in normalized_transactions if any(row.values())]

    def _build_prompt(self, *, structured_text: str, tables_markdown: str) -> str:
        return f"""
Extract the real bank transactions from this OCR output.

Rules:
- Return a JSON object with a single key called "transactions".
- Each transaction must have: date, description, amount.
- date must be ISO format YYYY-MM-DD when possible.
- amount must be a signed decimal string.
- Use negative values for outgoing money and positive values for incoming money.
- Exclude balance summaries, IBAN/BIC tables, legal text, support information,
  QR/help blocks and page footer text.
- Include pending transactions if they appear in a transactions table.
- If a row is split across multiple OCR rows, merge it into one transaction.
- If you are unsure, omit the row instead of inventing data.

Structured OCR:
{structured_text}

Tables:
{tables_markdown}
""".strip()
