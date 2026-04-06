from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.schemas import (
    ErrorResponse,
    PhoneNumberCreateRequest,
    PhoneNumberListResponse,
    PhoneNumberResponse,
    PhoneNumberUpdateRequest,
    utc_now,
)
from voiceagent_api.store import store
from voiceagent_api.routers._helpers import (
    require_idempotency_key,
    idempotency_request_hash,
)

router = APIRouter()


@router.get(
    "/v1/phone-numbers",
    response_model=PhoneNumberListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_phone_numbers(
    auth: AuthContext = Depends(require_scope("phone_numbers:read")),
    limit: int | None = None,
    offset: int = 0,
) -> PhoneNumberListResponse:
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = store.list_phone_numbers(auth.organization_id)
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    items = [PhoneNumberResponse.model_validate(item) for item in paged]
    return PhoneNumberListResponse(items=items, total=total)


@router.post(
    "/v1/phone-numbers",
    response_model=PhoneNumberResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def create_phone_number(
    payload: PhoneNumberCreateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("phone_numbers:write")),
) -> PhoneNumberResponse:
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
        return PhoneNumberResponse.model_validate(cached["response_body"])

    record = store.create_phone_number(payload, organization_id=auth.organization_id, now=utc_now())
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
    return PhoneNumberResponse.model_validate(record)


@router.patch(
    "/v1/phone-numbers/{number_id}",
    response_model=PhoneNumberResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def update_phone_number(
    number_id: str,
    payload: PhoneNumberUpdateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("phone_numbers:write")),
) -> PhoneNumberResponse:
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
        return PhoneNumberResponse.model_validate(cached["response_body"])

    record = store.update_phone_number(
        number_id,
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
    return PhoneNumberResponse.model_validate(record)
