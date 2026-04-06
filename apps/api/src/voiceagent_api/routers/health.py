from __future__ import annotations

from fastapi import APIRouter

from voiceagent_api.schemas import HealthResponse, ReadyResponse
from voiceagent_api.config import settings
from voiceagent_api.store import store

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    store.ping()
    return ReadyResponse(status="ready", environment=settings.env)
