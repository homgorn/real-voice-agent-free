from __future__ import annotations

from fastapi import APIRouter, Depends

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.schemas import (
    ErrorResponse,
    EventListResponse,
    EventResponse,
)
from voiceagent_api.store import store
from voiceagent_api.routers._helpers import normalize_pagination

router = APIRouter()


@router.get(
    "/v1/events",
    response_model=EventListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_events(
    auth: AuthContext = Depends(require_scope("events:read")),
    limit: int | None = None,
    offset: int = 0,
) -> EventListResponse:
    effective_limit, effective_offset = normalize_pagination(limit, offset)
    items, total = store.list_events_paginated(auth.organization_id, limit=effective_limit, offset=effective_offset)
    return EventListResponse(items=[EventResponse.model_validate(e) for e in items], total=total)
