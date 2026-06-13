"""Health-check endpoints — no auth required."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get("", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    from analytis import __version__

    return HealthResponse(status="ok", service="analytis", version=__version__)
