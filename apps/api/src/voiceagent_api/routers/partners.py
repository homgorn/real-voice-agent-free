from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.routers._helpers import (
    idempotency_request_hash,
    require_idempotency_key,
    trace_id_from_request,
)
from voiceagent_api.schemas import (
    ErrorResponse,
    PartnerAccountCreateRequest,
    PartnerAccountListResponse,
    PartnerAccountResponse,
    PartnerResponse,
    utc_now,
)
from voiceagent_api.store import store

router = APIRouter()


@router.get(
    "/v1/partners/current",
    response_model=PartnerResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_current_partner(
    auth: AuthContext = Depends(require_scope("partners:read")),
) -> PartnerResponse:
    record = store.get_partner(auth.organization_id)
    return PartnerResponse.model_validate(record)


@router.get(
    "/v1/partners/current/accounts",
    response_model=PartnerAccountListResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def list_partner_accounts(
    auth: AuthContext = Depends(require_scope("partners:read")),
    limit: int | None = None,
    offset: int = 0,
) -> PartnerAccountListResponse:
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = store.list_partner_accounts(auth.organization_id)
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    items = [PartnerAccountResponse.model_validate(item) for item in paged]
    return PartnerAccountListResponse(items=items, total=total)


@router.post(
    "/v1/partners/current/accounts",
    response_model=PartnerAccountResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def create_partner_account(
    payload: PartnerAccountCreateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("partners:write")),
) -> PartnerAccountResponse:
    trace_id = trace_id_from_request(request)
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
        return PartnerAccountResponse.model_validate(cached["response_body"])

    record = store.create_partner_account(
        payload,
        organization_id=auth.organization_id,
        trace_id=trace_id,
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
    return PartnerAccountResponse.model_validate(record)
