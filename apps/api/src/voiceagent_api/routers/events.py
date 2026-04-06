from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.schemas import (
    ErrorResponse,
    EventListResponse,
    EventResponse,
    utc_now,
)
from voiceagent_api.store import store

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
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = store.list_events(auth.organization_id)
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    items = [EventResponse.model_validate(event) for event in paged]
    return EventListResponse(items=items, total=total)
