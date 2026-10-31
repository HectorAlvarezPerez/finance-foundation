from __future__ import annotations

import argparse
import hashlib
import json

from langfuse import Langfuse

from app.core.config import settings
from app.llm.evals.cases import DATASET_DEFINITIONS
from app.llm.prompts import PROMPT_DEFINITIONS
from app.llm.types import ChatMessage


def _normalize_prompt_messages(messages: tuple[ChatMessage, ...]) -> list[dict[str, str]]:
    return [
        {"type": "message", "role": item["role"], "content": item["content"]} for item in messages
    ]


def _canonicalize_existing_prompt_messages(raw_messages: object) -> list[dict[str, str]] | None:
    if not isinstance(raw_messages, list):
        return None

    normalized: list[dict[str, str]] = []
    for raw_item in raw_messages:
        if not isinstance(raw_item, dict):
            return None

        role = raw_item.get("role")
        content = raw_item.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            return None

        normalized.append(
            {
                "type": "message",
                "role": role,
                "content": content,
            }
        )

    return normalized


def _dataset_item_id(dataset_name: str, case_name: str) -> str:
    digest = hashlib.sha1(f"{dataset_name}:{case_name}".encode("utf-8")).hexdigest()
    return digest[:32]


def bootstrap_prompts(client: Langfuse | None, *, label: str, dry_run: bool) -> list[str]:
    actions: list[str] = []
    for prompt_definition in PROMPT_DEFINITIONS.values():
        desired_prompt = _normalize_prompt_messages(prompt_definition.messages)
        needs_create = True
        if client is not None:
            try:
                existing = client.get_prompt(
                    prompt_definition.name,
                    label=label,
                    type="chat",
                    fallback=list(prompt_definition.messages),
                )
                existing_prompt = _canonicalize_existing_prompt_messages(
                    getattr(existing, "prompt", None)
                )
                if (
                    not getattr(existing, "is_fallback", False)
                    and existing_prompt == desired_prompt
                ):
                    needs_create = False
                    actions.append(f"prompt:{prompt_definition.name}:skip")
            except Exception:
                needs_create = True

        if needs_create:
            actions.append(f"prompt:{prompt_definition.name}:upsert")
            if client is not None and not dry_run:
                client.create_prompt(
                    name=prompt_definition.name,
                    prompt=list(prompt_definition.messages),
                    labels=[label],
                    type="chat",
                    commit_message="Bootstrap from finance-foundation repo",
                )
    return actions


def bootstrap_datasets(client: Langfuse | None, *, dry_run: bool) -> list[str]:
    actions: list[str] = []
    for dataset_name, definition in DATASET_DEFINITIONS.items():
        exists = False
        if client is not None:
            try:
                client.get_dataset(dataset_name)
                exists = True
            except Exception:
                exists = False

        if not exists:
            actions.append(f"dataset:{dataset_name}:create")
            if client is not None and not dry_run:
                client.create_dataset(
                    name=dataset_name,
                    description=definition["description"],
                )

        for item in definition["items"]:
            item_id = _dataset_item_id(dataset_name, item["name"])
            actions.append(f"dataset-item:{dataset_name}:{item['name']}:upsert")
            if client is not None and not dry_run:
                try:
                    client.create_dataset_item(
                        dataset_name=dataset_name,
                        id=item_id,
                        input=item["input"],
                        expected_output=item["expected_output"],
                        metadata=item["metadata"] | {"case_name": item["name"]},
                    )
                except Exception:
                    continue
    return actions


def build_client() -> Langfuse | None:
    if not settings.langfuse_enabled_configured:
        return None
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    client = build_client()
    actions = [
        *bootstrap_prompts(
            client,
            label=settings.langfuse_prompt_label,
            dry_run=args.dry_run,
        ),
        *bootstrap_datasets(client, dry_run=args.dry_run),
    ]

    if client is not None and not args.dry_run:
        client.flush()

    print(json.dumps({"actions": actions, "dry_run": args.dry_run}, ensure_ascii=False))


if __name__ == "__main__":
    main()
