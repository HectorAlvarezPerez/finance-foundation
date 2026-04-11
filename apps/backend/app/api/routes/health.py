from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.services import health_service

router = APIRouter()


@router.get("/health")
async def healthcheck() -> JSONResponse:
    is_healthy, database_status = health_service.get_health_status()
    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    health_status = "ok" if is_healthy else "error"

    return JSONResponse(
        status_code=status_code,
        content={"status": health_status, "checks": {"database": database_status}},
    )
