from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.routers._helpers import (
    idempotency_request_hash,
    require_idempotency_key,
)
from voiceagent_api.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyDeleteResponse,
    ApiKeyListResponse,
    ApiKeyMetadataResponse,
    ErrorResponse,
    utc_now,
)
from voiceagent_api.store import store

router = APIRouter()


@router.get(
    "/v1/api-keys",
    response_model=ApiKeyListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_api_keys(
    auth: AuthContext = Depends(require_scope("api_keys:read")),
    limit: int | None = None,
    offset: int = 0,
) -> ApiKeyListResponse:
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = store.list_api_keys(auth.organization_id)
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    items = [ApiKeyMetadataResponse.model_validate(item) for item in paged]
    return ApiKeyListResponse(items=items, total=total)


@router.post(
    "/v1/api-keys",
    response_model=ApiKeyCreateResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("api_keys:write")),
) -> ApiKeyCreateResponse:
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
        return ApiKeyCreateResponse.model_validate(cached["response_body"])

    record = store.create_api_key(
        payload, organization_id=auth.organization_id, now=utc_now()
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
    return ApiKeyCreateResponse.model_validate(record)


@router.delete(
    "/v1/api-keys/{key_id}",
    response_model=ApiKeyDeleteResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def delete_api_key(
    key_id: str,
    auth: AuthContext = Depends(require_scope("api_keys:write")),
) -> ApiKeyDeleteResponse:
    record = store.delete_api_key(key_id, organization_id=auth.organization_id)
    return ApiKeyDeleteResponse.model_validate(record)
