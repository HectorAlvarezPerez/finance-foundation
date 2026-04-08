#!/usr/bin/env python3
"""Post non-blocking operational deploy notifications to Slack."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib import error, parse, request

HEX_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)
TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_LANGFUSE_DEPLOY_PROMPT_NAME = "deploy_summary_notification"


@dataclass
class ResolvedSummaryPrompt:
    name: str
    label: str
    version: int | None
    source: str
    messages: list[dict[str, str]]
    prompt_client: Any | None = None


@dataclass
class LangfuseFlowHandle:
    name: str
    span: Any | None = None
    context_manager: Any | None = None

    @property
    def observation_id(self) -> str | None:
        return getattr(self.span, "id", None)

    @property
    def trace_id(self) -> str | None:
        return getattr(self.span, "trace_id", None)


@dataclass
class NarrativeContext:
    kind: str
    heading: str
    details: list[str]
    summary_hint: str


class DeployLangfuseClient:
    def __init__(self) -> None:
        self.langfuse_enabled = os.environ.get("LANGFUSE_ENABLED", "false").strip().lower() in TRUE_VALUES
        self.public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
        self.secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
        self.host = os.environ.get("LANGFUSE_HOST")
        self.env = os.environ.get("LANGFUSE_ENV") or os.environ.get("APP_ENV") or "production"
        self.prompt_label = os.environ.get("LANGFUSE_PROMPT_LABEL", "production")
        self.deploy_prompt_name = os.environ.get(
            "LANGFUSE_DEPLOY_SUMMARY_PROMPT_NAME",
            DEFAULT_LANGFUSE_DEPLOY_PROMPT_NAME,
        )
        self.client = self._build_client()

    def _build_client(self) -> Any | None:
        if not self.is_configured:
            return None

        try:
            from langfuse import Langfuse  # type: ignore[import-not-found]
        except Exception as exc:
            log(f"Langfuse SDK unavailable: {exc}")
            return None

        try:
            return Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host,
            )
        except Exception as exc:
            log(f"Failed to initialize Langfuse client: {exc}")
            return None

    @property
    def is_configured(self) -> bool:
        return bool(
            self.langfuse_enabled
            and self.public_key
            and self.secret_key
            and self.host
        )

    @property
    def is_enabled(self) -> bool:
        return self.client is not None

    def resolve_prompt(
        self,
        *,
        variables: dict[str, Any],
        fallback_messages: list[dict[str, str]],
    ) -> ResolvedSummaryPrompt:
        rendered_fallback = render_prompt_messages(fallback_messages, variables)
        if not self.is_enabled:
            return ResolvedSummaryPrompt(
                name=self.deploy_prompt_name,
                label=self.prompt_label,
                version=None,
                source="local_fallback",
                messages=rendered_fallback,
            )

        client = self.client
        if client is None:
            return ResolvedSummaryPrompt(
                name=self.deploy_prompt_name,
                label=self.prompt_label,
                version=None,
                source="local_fallback",
                messages=rendered_fallback,
            )

        try:
            prompt_client = client.get_prompt(
                self.deploy_prompt_name,
                label=self.prompt_label,
                type="chat",
                fallback=list(fallback_messages),
            )
            compiled = prompt_client.compile(**variables)
            normalized_messages: list[dict[str, str]] = []
            for message in compiled:
                if not isinstance(message, dict):
                    continue
                normalized_messages.append(
                    {
                        "role": str(message.get("role", "user")),
                        "content": compact_text(str(message.get("content", ""))),
                    }
                )
            if not normalized_messages:
                raise ValueError("compiled prompt is empty")

            return ResolvedSummaryPrompt(
                name=self.deploy_prompt_name,
                label=self.prompt_label,
                version=getattr(prompt_client, "version", None),
                source="langfuse",
                messages=normalized_messages,
                prompt_client=prompt_client,
            )
        except Exception as exc:
            log(f"Failed to fetch Langfuse prompt '{self.deploy_prompt_name}': {exc}")
            return ResolvedSummaryPrompt(
                name=self.deploy_prompt_name,
                label=self.prompt_label,
                version=None,
                source="local_fallback",
                messages=rendered_fallback,
            )

    def start_flow(
        self,
        *,
        name: str,
        input_payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> LangfuseFlowHandle | None:
        if not self.is_enabled:
            return None

        client = self.client
        if client is None:
            return None

        try:
            context_manager = client.start_as_current_observation(
                name=name,
                as_type="span",
                input=input_payload,
                metadata=metadata,
                end_on_exit=False,
            )
            span = context_manager.__enter__()
            return LangfuseFlowHandle(name=name, span=span, context_manager=context_manager)
        except Exception as exc:
            log(f"Failed to start Langfuse flow '{name}': {exc}")
            return None

    def end_flow(
        self,
        handle: LangfuseFlowHandle | None,
        *,
        output_payload: dict[str, Any] | None,
        metadata: dict[str, Any],
        status_message: str | None = None,
        level: str | None = None,
    ) -> None:
        if handle is None or handle.span is None or handle.context_manager is None:
            return

        try:
            handle.span.update(
                output=output_payload,
                metadata=metadata,
                status_message=status_message,
                level=level,
            )
        except Exception as exc:
            log(f"Failed to update Langfuse flow '{handle.name}': {exc}")
        finally:
            try:
                handle.span.end()
                handle.context_manager.__exit__(None, None, None)
            except Exception as exc:
                log(f"Failed to close Langfuse flow '{handle.name}': {exc}")

    def record_generation(
        self,
        *,
        handle: LangfuseFlowHandle | None,
        name: str,
        model: str | None,
        prompt: ResolvedSummaryPrompt,
        input_payload: dict[str, Any],
        output_payload: dict[str, Any] | None,
        usage: dict[str, int] | None,
        metadata: dict[str, Any],
        status_message: str | None = None,
        level: str | None = None,
    ) -> None:
        if not self.is_enabled:
            return

        client = self.client
        if client is None:
            return

        trace_context: dict[str, str] | None = None
        if handle and handle.trace_id and handle.observation_id:
            trace_context = {
                "trace_id": handle.trace_id,
                "parent_observation_id": handle.observation_id,
            }

        try:
            with client.start_as_current_observation(
                trace_context=trace_context,
                name=name,
                as_type="generation",
                input=input_payload,
                output=output_payload,
                metadata=metadata,
                model=model,
                usage_details=usage,
                prompt=prompt.prompt_client,
                status_message=status_message,
                level=level,
            ):
                return None
        except Exception as exc:
            log(f"Failed to record Langfuse generation '{name}': {exc}")

    def flush(self) -> None:
        if not self.is_enabled:
            return

        client = self.client
        if client is None:
            return

        try:
            client.flush()
        except Exception as exc:
            log(f"Failed to flush Langfuse client: {exc}")


@lru_cache(maxsize=1)
def get_langfuse_client() -> DeployLangfuseClient:
    return DeployLangfuseClient()


def log(message: str) -> None:
    print(f"[deploy-notify] {message}", file=sys.stderr)


def compact_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().split())


def shorten(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def render_template_string(template: str, variables: dict[str, Any]) -> str:
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", "" if value is None else str(value))
    return compact_text(rendered)


def render_prompt_messages(
    messages: list[dict[str, str]],
    variables: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {
            "role": message.get("role", "user"),
            "content": render_template_string(message.get("content", ""), variables),
        }
        for message in messages
    ]


def run_command(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip()


def git_output(*args: str) -> str | None:
    return run_command(["git", *args])


def get_repo_slug() -> str | None:
    remote = git_output("config", "--get", "remote.origin.url")
    if not remote:
        return None

    if remote.startswith("git@github.com:"):
        slug = remote.split("git@github.com:", 1)[1]
    elif remote.startswith("https://github.com/"):
        slug = remote.split("https://github.com/", 1)[1]
    else:
        return None

    return slug.removesuffix(".git")


def resolve_pr_context(repo_slug: str | None, commit_sha: str) -> NarrativeContext | None:
    if not repo_slug or not shutil.which("gh"):
        return None

    output = run_command(
        [
            "gh",
            "api",
            "-H",
            "Accept: application/vnd.github+json",
            f"/repos/{repo_slug}/commits/{commit_sha}/pulls",
        ]
    )
    if not output:
        return None

    try:
        pulls = json.loads(output)
    except json.JSONDecodeError:
        return None

    if not pulls:
        return None

    pr = next((item for item in pulls if item.get("merged_at")), pulls[0])
    number = pr.get("number")
    title = compact_text(pr.get("title"))
    body = compact_text(pr.get("body"))
    link = pr.get("html_url")

    details = [f"PR #{number}: {title}"]
    if body:
        details.append(f"Resumen de la PR: {body}")
    if link:
        details.append(f"URL de la PR: {link}")

    summary_hint = f"PR #{number}: {title}" if number else title or "PR mergeada"
    return NarrativeContext(
        kind="pull-request",
        heading="Contexto detectado a partir de la pull request mergeada asociada al commit desplegado.",
        details=details,
        summary_hint=summary_hint,
    )


def extract_commit_from_image(image: str | None) -> str | None:
    if not image or ":" not in image:
        return None

    tag = image.rsplit(":", 1)[1].strip()
    if not HEX_SHA_RE.match(tag):
        return None

    resolved = git_output("rev-parse", "--verify", "--quiet", f"{tag}^{{commit}}")
    if not resolved:
        return None
    return tag


def resolve_range_context(previous_image: str | None, commit_sha: str) -> NarrativeContext | None:
    previous_commit = extract_commit_from_image(previous_image)
    if not previous_commit:
        return None

    if not git_output("rev-parse", "--verify", "--quiet", f"{commit_sha}^{{commit}}"):
        return None

    output = git_output(
        "log",
        "--reverse",
        "--pretty=format:%h %s",
        f"{previous_commit}..{commit_sha}",
    )
    if not output:
        return None

    commits = [line.strip() for line in output.splitlines() if line.strip()]
    if not commits:
        return None

    visible_commits = commits[:6]
    details = [f"Rango de commits: {previous_commit[:7]}..{commit_sha[:7]}"]
    details.extend(visible_commits)
    summary_hint = "; ".join(item.split(" ", 1)[1] if " " in item else item for item in commits[:3])
    return NarrativeContext(
        kind="commit-range",
        heading="Contexto detectado a partir del rango de commits entre la imagen previa y el commit desplegado.",
        details=details,
        summary_hint=summary_hint,
    )


def resolve_commit_context(commit_sha: str) -> NarrativeContext | None:
    subject = compact_text(git_output("show", "-s", "--format=%s", commit_sha))
    body = compact_text(git_output("show", "-s", "--format=%b", commit_sha))
    if not subject and not body:
        return None

    details = [f"Commit: {commit_sha[:7]} {subject or 'sin asunto disponible'}"]
    if body:
        details.append(f"Detalle del commit: {body}")

    return NarrativeContext(
        kind="commit",
        heading="Contexto detectado a partir del commit desplegado.",
        details=details,
        summary_hint=subject or f"commit {commit_sha[:7]}",
    )


def collect_recent_commit_titles(commit_sha: str, *, limit: int = 6) -> list[str]:
    output = git_output(
        "log",
        f"-n{limit}",
        "--pretty=format:%h %s",
        commit_sha,
    )
    if not output:
        return []

    return [line.strip() for line in output.splitlines() if line.strip()]


def resolve_context(commit_sha: str, previous_image: str | None) -> NarrativeContext | None:
    repo_slug = get_repo_slug()
    context = (
        resolve_pr_context(repo_slug, commit_sha)
        or resolve_range_context(previous_image, commit_sha)
        or resolve_commit_context(commit_sha)
    )

    if context is None:
        return None

    if context.kind != "commit-range":
        recent_titles = collect_recent_commit_titles(commit_sha, limit=6)
        if recent_titles:
            context.details.append("Commits recientes (títulos):")
            context.details.extend(recent_titles)

    return context


def build_fallback_summary(
    service: str,
    environment: str,
    image: str,
    commit_sha: str,
    context: NarrativeContext | None,
) -> str:
    if context and context.kind == "pull-request":
        return (
            f"Se ha desplegado `{service}` en `{environment}` con el commit `{commit_sha[:7]}`. "
            f"El cambio principal corresponde a {context.summary_hint}."
        )
    if context and context.kind == "commit-range":
        return (
            f"Se ha desplegado `{service}` en `{environment}` con la imagen `{image}`. "
            f"El release agrupa cambios recientes: {context.summary_hint or 'varios commits del rango detectado'}."
        )
    if context and context.kind == "commit":
        return (
            f"Se ha desplegado `{service}` en `{environment}` con el commit `{commit_sha[:7]}`. "
            f"El cambio publicado corresponde a {context.summary_hint}."
        )
    return (
        f"Se ha desplegado `{service}` en `{environment}` con la imagen `{image}` y el commit "
        f"`{commit_sha[:7]}`. No se pudo obtener más contexto del cambio."
    )


def azure_openai_enabled() -> bool:
    return all(
        [
            os.environ.get("AZURE_OPENAI_ENDPOINT"),
            os.environ.get("AZURE_OPENAI_API_KEY"),
            os.environ.get("AZURE_OPENAI_DEPLOY_SUMMARY_DEPLOYMENT"),
        ]
    )


def build_deploy_summary_prompt_messages() -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Eres un asistente de release notes operativas. Responde solo con un párrafo breve, "
                "claro y factual en español."
            ),
        },
        {
            "role": "user",
            "content": textwrap.dedent(
                """
                Resume en español, en un único párrafo breve de 1 a 3 frases, qué se ha desplegado.
                No inventes detalles ni menciones que se ha usado un LLM.
                Prioriza lo que cambia a nivel operativo o funcional.

                Servicio: {{service}}
                Entorno: {{environment}}
                Commit: {{commit_sha_short}}
                Imagen: {{image}}
                URL: {{url}}

                {{context_heading}}
                {{context_block}}
                """
            ).strip(),
        },
    ]


def build_deploy_summary_prompt_variables(
    *,
    service: str,
    environment: str,
    image: str,
    url: str,
    commit_sha: str,
    context: NarrativeContext,
) -> dict[str, str]:
    context_block = "\n".join(f"- {detail}" for detail in context.details)
    return {
        "service": service,
        "environment": environment,
        "commit_sha_short": commit_sha[:7],
        "image": image,
        "url": url,
        "context_heading": context.heading,
        "context_block": context_block,
    }


def extract_usage(response_payload: dict[str, Any]) -> dict[str, int] | None:
    usage_payload = response_payload.get("usage")
    if not isinstance(usage_payload, dict):
        return None

    normalized_usage: dict[str, int] = {}
    for key in ["prompt_tokens", "completion_tokens", "total_tokens"]:
        value = usage_payload.get(key)
        if isinstance(value, int):
            normalized_usage[key] = value
    return normalized_usage or None


def extract_chat_message(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices") or []
    if not choices:
        return ""

    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return compact_text(content)
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text_value = item.get("text")
                if text_value:
                    parts.append(str(text_value))
        return compact_text(" ".join(parts))
    return ""


def generate_llm_summary(
    service: str,
    environment: str,
    image: str,
    url: str,
    commit_sha: str,
    context: NarrativeContext | None,
    langfuse_client: DeployLangfuseClient,
) -> str | None:
    if not context:
        return None

    if not azure_openai_enabled():
        return None

    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    deployment = os.environ["AZURE_OPENAI_DEPLOY_SUMMARY_DEPLOYMENT"]
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")

    prompt_variables = build_deploy_summary_prompt_variables(
        service=service,
        environment=environment,
        image=image,
        url=url,
        commit_sha=commit_sha,
        context=context,
    )
    resolved_prompt = langfuse_client.resolve_prompt(
        variables=prompt_variables,
        fallback_messages=build_deploy_summary_prompt_messages(),
    )
    flow_handle = langfuse_client.start_flow(
        name="deploy_notify_summary",
        input_payload={
            "service": service,
            "environment": environment,
            "image": image,
            "url": url,
            "commit_sha": commit_sha,
            "prompt_name": resolved_prompt.name,
            "prompt_label": resolved_prompt.label,
            "prompt_source": resolved_prompt.source,
            "prompt_version": resolved_prompt.version,
            "context_kind": context.kind,
        },
        metadata={
            "service": service,
            "environment": environment,
            "prompt_name": resolved_prompt.name,
            "prompt_label": resolved_prompt.label,
            "prompt_source": resolved_prompt.source,
            "prompt_version": resolved_prompt.version,
        },
    )

    payload_variants = [
        {
            "messages": resolved_prompt.messages,
            "max_tokens": 180,
            "temperature": 0.2,
        },
        {
            "messages": resolved_prompt.messages,
            "max_completion_tokens": 180,
            "temperature": 0.2,
        },
    ]

    request_url = (
        f"{endpoint}/openai/deployments/{parse.quote(deployment)}/chat/completions"
        f"?api-version={parse.quote(api_version)}"
    )
    response_payload: dict[str, Any] | None = None
    last_error: Exception | None = None
    for variant_index, payload in enumerate(payload_variants):
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            request_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "api-key": os.environ["AZURE_OPENAI_API_KEY"],
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=20) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
                break
        except error.HTTPError as exc:
            last_error = exc
            should_retry_next = exc.code == 400 and variant_index + 1 < len(payload_variants)
            if should_retry_next:
                continue
            break
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            break

    if response_payload is None:
        exc = last_error or RuntimeError("unknown Azure OpenAI error")
        log(f"Azure OpenAI summary failed: {exc}")
        langfuse_client.record_generation(
            handle=flow_handle,
            name="deploy_notify_openai_generation",
            model=deployment,
            prompt=resolved_prompt,
            input_payload=prompt_variables,
            output_payload=None,
            usage=None,
            metadata={
                "deployment": deployment,
                "api_version": api_version,
                "prompt_source": resolved_prompt.source,
                "prompt_version": resolved_prompt.version,
            },
            status_message=str(exc),
            level="ERROR",
        )
        langfuse_client.end_flow(
            flow_handle,
            output_payload=None,
            metadata={
                "deployment": deployment,
                "api_version": api_version,
                "status": "error",
            },
            status_message=str(exc),
            level="ERROR",
        )
        return None

    summary = extract_chat_message(response_payload)
    usage = extract_usage(response_payload)
    if not summary:
        log("Azure OpenAI summary failed: empty response.")
        langfuse_client.record_generation(
            handle=flow_handle,
            name="deploy_notify_openai_generation",
            model=deployment,
            prompt=resolved_prompt,
            input_payload=prompt_variables,
            output_payload={"raw_response": response_payload},
            usage=usage,
            metadata={
                "deployment": deployment,
                "api_version": api_version,
                "prompt_source": resolved_prompt.source,
                "prompt_version": resolved_prompt.version,
                "invalid_reason": "llm_empty_summary",
            },
            status_message="Empty summary response",
            level="WARNING",
        )
        langfuse_client.end_flow(
            flow_handle,
            output_payload={"raw_response": response_payload},
            metadata={
                "deployment": deployment,
                "api_version": api_version,
                "status": "warning",
                "invalid_reason": "llm_empty_summary",
            },
            status_message="Empty summary response",
            level="WARNING",
        )
        return None

    langfuse_client.record_generation(
        handle=flow_handle,
        name="deploy_notify_openai_generation",
        model=deployment,
        prompt=resolved_prompt,
        input_payload=prompt_variables,
        output_payload={
            "summary": summary,
            "raw_response": response_payload,
        },
        usage=usage,
        metadata={
            "deployment": deployment,
            "api_version": api_version,
            "prompt_source": resolved_prompt.source,
            "prompt_version": resolved_prompt.version,
        },
    )
    langfuse_client.end_flow(
        flow_handle,
        output_payload={"summary": summary},
        metadata={
            "deployment": deployment,
            "api_version": api_version,
            "status": "ok",
            "prompt_source": resolved_prompt.source,
            "prompt_version": resolved_prompt.version,
        },
    )

    return summary


def post_to_slack(payload: dict[str, Any]) -> None:
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        log("Skipping Slack notification: SLACK_WEBHOOK_URL is not configured.")
        return

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        webhook,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as response:
            response.read()
    except (error.URLError, error.HTTPError, TimeoutError) as exc:
        log(f"Slack notification failed: {exc}")
        return

    log("Slack notification sent.")


def build_slack_payload(
    service: str,
    environment: str,
    image: str,
    url: str,
    commit_sha: str,
    summary: str,
) -> dict[str, Any]:
    short_sha = commit_sha[:7]
    headline = f"Deploy a producción completado: {service}"
    details = (
        f"*Servicio:* `{service}`\n"
        f"*Entorno:* `{environment}`\n"
        f"*Commit:* `{short_sha}`\n"
        f"*Imagen:* `{image}`\n"
        f"*URL:* <{url}|{url}>"
    )

    return {
        "text": f"{headline} ({short_sha})",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{headline}*\n{details}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": summary,
                },
            },
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Notify Slack after a successful deploy.")
    parser.add_argument("--service", required=True, choices=["backend", "frontend"])
    parser.add_argument("--environment", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--previous-image")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    langfuse_client = get_langfuse_client()
    context = resolve_context(args.commit_sha, args.previous_image)
    summary = generate_llm_summary(
        service=args.service,
        environment=args.environment,
        image=args.image,
        url=args.url,
        commit_sha=args.commit_sha,
        context=context,
        langfuse_client=langfuse_client,
    ) or build_fallback_summary(
        service=args.service,
        environment=args.environment,
        image=args.image,
        commit_sha=args.commit_sha,
        context=context,
    )

    payload = build_slack_payload(
        service=args.service,
        environment=args.environment,
        image=args.image,
        url=args.url,
        commit_sha=args.commit_sha,
        summary=summary,
    )
    post_to_slack(payload)
    langfuse_client.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
