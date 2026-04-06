from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.schemas import (
    ErrorResponse,
    IntegrationConnectRequest,
    IntegrationListResponse,
    IntegrationResponse,
    IntegrationTestResponse,
    utc_now,
)
from voiceagent_api.store import store
from voiceagent_api.routers._helpers import (
    require_idempotency_key,
    idempotency_request_hash,
)

router = APIRouter()


@router.get(
    "/v1/integrations",
    response_model=IntegrationListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_integrations(
    auth: AuthContext = Depends(require_scope("integrations:read")),
    limit: int | None = None,
    offset: int = 0,
) -> IntegrationListResponse:
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = store.list_integrations(auth.organization_id)
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    items = [IntegrationResponse.model_validate(item) for item in paged]
    return IntegrationListResponse(items=items, total=total)


@router.post(
    "/v1/integrations/{provider}/connect",
    response_model=IntegrationResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def connect_integration(
    provider: str,
    payload: IntegrationConnectRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("integrations:write")),
) -> IntegrationResponse:
    idempotency_key = require_idempotency_key(request)
    request_hash = idempotency_request_hash(
        payload.model_dump(),
        path=request.url.path,
        method=request.method,
    )
    cached = store.get_idempotent_response(
        organization_id=auth.organization_id,
        key=idempotency_key,
        method=request.method,
        path=request.url.path,
        request_hash=request_hash,
    )
    if cached:
        return IntegrationResponse.model_validate(cached["response_body"])

    record = store.connect_integration(
        provider,
        payload,
        organization_id=auth.organization_id,
        now=utc_now(),
    )
    store.store_idempotent_response(
        organization_id=auth.organization_id,
        key=idempotency_key,
        method=request.method,
        path=request.url.path,
        request_hash=request_hash,
        response_body=record,
        response_code=200,
        created_at=utc_now(),
    )
    return IntegrationResponse.model_validate(record)


@router.post(
    "/v1/integrations/{provider}/test",
    response_model=IntegrationTestResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def test_integration(
    provider: str,
    request: Request,
    auth: AuthContext = Depends(require_scope("integrations:write")),
) -> IntegrationTestResponse:
    idempotency_key = require_idempotency_key(request)
    request_hash = idempotency_request_hash(
        {},
        path=request.url.path,
        method=request.method,
    )
    cached = store.get_idempotent_response(
        organization_id=auth.organization_id,
        key=idempotency_key,
        method=request.method,
        path=request.url.path,
        request_hash=request_hash,
    )
    if cached:
        return IntegrationTestResponse.model_validate(cached["response_body"])

    record = store.test_integration(
        provider,
        organization_id=auth.organization_id,
        now=utc_now(),
    )
    store.store_idempotent_response(
        organization_id=auth.organization_id,
        key=idempotency_key,
        method=request.method,
        path=request.url.path,
        request_hash=request_hash,
        response_body=record,
        response_code=200,
        created_at=utc_now(),
    )
    return IntegrationTestResponse.model_validate(record)
