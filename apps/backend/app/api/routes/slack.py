from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status

from app.services.slack_docs_bot_service import SlackDocsBotService

router = APIRouter(prefix="/slack", tags=["slack"])


def get_slack_docs_bot_service() -> SlackDocsBotService:
    service = SlackDocsBotService()
    service.require_configured()
    return service


SlackDocsBotServiceDep = Annotated[SlackDocsBotService, Depends(get_slack_docs_bot_service)]


@router.post("/events")
async def handle_slack_events(
    request: Request,
    background_tasks: BackgroundTasks,
    service: SlackDocsBotServiceDep,
    x_slack_request_timestamp: str | None = Header(default=None),
    x_slack_signature: str | None = Header(default=None),
) -> dict[str, str | bool]:
    body = await request.body()
    if not service.verify_request(
        body=body,
        timestamp=x_slack_request_timestamp,
        signature=x_slack_signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Slack signature",
        )

    payload = await request.json()
    response_payload = service.handle_event_payload(payload)
    if payload.get("type") == "event_callback":
        background_tasks.add_task(service.process_event, payload)
    return response_payload
