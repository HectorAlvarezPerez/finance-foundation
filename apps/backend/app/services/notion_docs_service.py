from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings

TITLE_PROPERTY_CANDIDATES = ("Title", "title", "Name", "name")
TOKEN_PATTERN = re.compile(r"[a-z0-9]{3,}")


@dataclass(frozen=True)
class NotionKnowledgeDocument:
    page_id: str
    title: str
    url: str
    category: str | None
    audience: str | None
    surface: str | None
    status: str | None
    source_type: str | None
    source_ref: str | None
    slack_ready: bool
    faq_seeds: str | None
    content: str


@dataclass(frozen=True)
class NotionDocumentMatch:
    document: NotionKnowledgeDocument
    score: int
    snippet: str


class NotionDocsService:
    def __init__(
        self,
        *,
        token: str | None = None,
        data_source_id: str | None = None,
        cache_ttl_seconds: int | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.token = token or settings.notion_api_token
        self.data_source_id = data_source_id or settings.notion_docs_data_source_id
        self.notion_api_version = settings.notion_api_version
        self.cache_ttl_seconds = cache_ttl_seconds or settings.notion_docs_cache_ttl_seconds
        self.timeout_seconds = timeout_seconds
        self._cache_expires_at = 0.0
        self._cache_documents: list[NotionKnowledgeDocument] = []

    @property
    def is_configured(self) -> bool:
        return self.token is not None and self.data_source_id is not None

    def list_documents(self, *, refresh: bool = False) -> list[NotionKnowledgeDocument]:
        if not self.is_configured:
            return []

        if not refresh and self._cache_expires_at > time.time():
            return list(self._cache_documents)

        documents = self._fetch_documents()
        self._cache_documents = documents
        self._cache_expires_at = time.time() + max(30, self.cache_ttl_seconds)
        return list(documents)

    def search_documents(self, query: str, *, limit: int = 3) -> list[NotionDocumentMatch]:
        documents = self.list_documents()
        if not documents:
            return []

        tokens = self._tokenize(query)
        matches: list[NotionDocumentMatch] = []
        for document in documents:
            score = self._score_document(document, tokens)
            if score <= 0:
                continue
            matches.append(
                NotionDocumentMatch(
                    document=document,
                    score=score,
                    snippet=self._build_snippet(document.content, tokens),
                )
            )

        matches.sort(
            key=lambda item: (
                item.score,
                item.document.slack_ready,
                len(item.document.content),
            ),
            reverse=True,
        )
        return matches[:limit]

    def _fetch_documents(self) -> list[NotionKnowledgeDocument]:
        assert self.token is not None
        assert self.data_source_id is not None

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": self.notion_api_version,
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {"page_size": 100}
        documents: list[NotionKnowledgeDocument] = []

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"https://api.notion.com/v1/data_sources/{self.data_source_id}/query",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            results = response.json().get("results", [])

            for item in results:
                if not isinstance(item, dict):
                    continue
                properties = item.get("properties")
                if not isinstance(properties, dict):
                    continue

                status_value = self._get_property_value(properties, "Status")
                if status_value not in {None, "", "Ready", "Done"}:
                    continue

                content = self._read_page_content(client, headers, page_id=str(item["id"]))
                documents.append(
                    NotionKnowledgeDocument(
                        page_id=str(item["id"]),
                        title=self._get_title(properties),
                        url=str(item.get("url", "")),
                        category=self._get_property_value(properties, "Category"),
                        audience=self._get_property_value(properties, "Audience"),
                        surface=self._get_property_value(properties, "Surface"),
                        status=status_value,
                        source_type=self._get_property_value(properties, "Source Type"),
                        source_ref=self._get_property_value(properties, "Source Ref"),
                        slack_ready=self._get_property_checkbox(properties, "Slack Ready"),
                        faq_seeds=self._get_property_value(properties, "FAQ Seeds"),
                        content=content,
                    )
                )

        return documents

    def _read_page_content(
        self,
        client: httpx.Client,
        headers: dict[str, str],
        *,
        page_id: str,
    ) -> str:
        lines = self._read_block_children(client, headers, block_id=page_id)
        return "\n".join(line for line in lines if line).strip()

    def _read_block_children(
        self,
        client: httpx.Client,
        headers: dict[str, str],
        *,
        block_id: str,
    ) -> list[str]:
        response = client.get(
            f"https://api.notion.com/v1/blocks/{block_id}/children",
            headers=headers,
            params={"page_size": 100},
        )
        response.raise_for_status()
        payload = response.json()
        lines: list[str] = []
        for block in payload.get("results", []):
            if not isinstance(block, dict):
                continue
            block_type = str(block.get("type", ""))
            block_payload = block.get(block_type)
            if isinstance(block_payload, dict):
                text = self._extract_text_from_block_payload(block_payload)
                if text:
                    lines.append(text)
            if bool(block.get("has_children")):
                lines.extend(
                    self._read_block_children(
                        client,
                        headers,
                        block_id=str(block["id"]),
                    )
                )
        return lines

    def _extract_text_from_block_payload(self, payload: dict[str, Any]) -> str:
        parts: list[str] = []
        for key in ("rich_text", "caption"):
            raw_value = payload.get(key)
            if isinstance(raw_value, list):
                parts.extend(
                    str(item.get("plain_text", ""))
                    for item in raw_value
                    if isinstance(item, dict) and item.get("plain_text")
                )
        if not parts and isinstance(payload.get("title"), list):
            parts.extend(
                str(item.get("plain_text", ""))
                for item in payload["title"]
                if isinstance(item, dict) and item.get("plain_text")
            )
        if not parts and isinstance(payload.get("checked"), bool):
            return "Checked" if payload["checked"] else "Unchecked"
        return " ".join(part.strip() for part in parts if part.strip())

    def _get_title(self, properties: dict[str, Any]) -> str:
        for candidate in TITLE_PROPERTY_CANDIDATES:
            value = properties.get(candidate)
            if isinstance(value, dict) and value.get("type") == "title":
                title = self._extract_property_text(value)
                if title:
                    return title

        for value in properties.values():
            if isinstance(value, dict) and value.get("type") == "title":
                title = self._extract_property_text(value)
                if title:
                    return title

        return "Untitled document"

    def _get_property_value(self, properties: dict[str, Any], name: str) -> str | None:
        property_value = properties.get(name)
        if not isinstance(property_value, dict):
            return None
        return self._extract_property_text(property_value)

    def _get_property_checkbox(self, properties: dict[str, Any], name: str) -> bool:
        property_value = properties.get(name)
        if not isinstance(property_value, dict):
            return False
        if property_value.get("type") != "checkbox":
            return False
        return bool(property_value.get("checkbox"))

    def _extract_property_text(self, property_value: dict[str, Any]) -> str | None:
        property_type = property_value.get("type")
        raw_value = property_value.get(str(property_type))
        if property_type in {"title", "rich_text"} and isinstance(raw_value, list):
            text = "".join(
                str(item.get("plain_text", ""))
                for item in raw_value
                if isinstance(item, dict)
            ).strip()
            return text or None
        if property_type in {"select", "status"} and isinstance(raw_value, dict):
            name = raw_value.get("name")
            return str(name) if isinstance(name, str) and name else None
        if property_type == "multi_select" and isinstance(raw_value, list):
            values = [
                str(item.get("name"))
                for item in raw_value
                if isinstance(item, dict) and item.get("name")
            ]
            return ", ".join(values) if values else None
        if property_type == "checkbox":
            return "Yes" if bool(raw_value) else "No"
        if property_type == "url" and isinstance(raw_value, str):
            return raw_value or None
        if property_type == "number" and isinstance(raw_value, int | float):
            return str(raw_value)
        return None

    def _tokenize(self, text: str) -> set[str]:
        return {match.group(0) for match in TOKEN_PATTERN.finditer(text.lower())}

    def _score_document(self, document: NotionKnowledgeDocument, tokens: set[str]) -> int:
        if not tokens:
            return 1 if document.slack_ready else 0

        haystacks = {
            "title": document.title.lower(),
            "category": (document.category or "").lower(),
            "surface": (document.surface or "").lower(),
            "faq": (document.faq_seeds or "").lower(),
            "content": document.content.lower(),
        }
        score = 0
        for token in tokens:
            if token in haystacks["title"]:
                score += 8
            if token in haystacks["surface"]:
                score += 6
            if token in haystacks["category"]:
                score += 4
            if token in haystacks["faq"]:
                score += 3
            if token in haystacks["content"]:
                score += 1

        if document.slack_ready:
            score += 2
        return score

    def _build_snippet(self, content: str, tokens: set[str], *, window: int = 220) -> str:
        if not content:
            return ""
        if not tokens:
            return content[:window].strip()

        lowered = content.lower()
        positions = [lowered.find(token) for token in tokens if lowered.find(token) >= 0]
        if not positions:
            return content[:window].strip()

        start = max(0, min(positions) - 60)
        end = min(len(content), start + window)
        snippet = content[start:end].strip()
        if start > 0:
            snippet = f"...{snippet}"
        if end < len(content):
            snippet = f"{snippet}..."
        return snippet
