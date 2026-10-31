from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.services import health_service

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse},
    },
)
async def healthcheck(response: Response) -> HealthResponse:
    is_healthy, database_status = health_service.get_health_status()
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    health_status = "ok" if is_healthy else "error"
    return HealthResponse(status=health_status, checks={"database": database_status})
