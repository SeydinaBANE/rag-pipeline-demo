from __future__ import annotations

from fastapi import APIRouter

from src.api.schemas import HealthResponse
from src.config import get_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    s = get_settings()
    return HealthResponse(status="ok", version=s.app_version, environment=s.environment)


@router.get("/ready", response_model=HealthResponse)
def ready() -> HealthResponse:
    s = get_settings()
    return HealthResponse(status="ok", version=s.app_version, environment=s.environment)
