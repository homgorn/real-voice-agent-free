from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.routers._helpers import (
    idempotency_request_hash,
    normalize_pagination,
    require_idempotency_key,
    trace_id_from_request,
)
from voiceagent_api.schemas import (
    CallCompleteRequest,
    CallCreateRequest,
    CallListResponse,
    CallRespondRequest,
    CallResponse,
    CallSummaryResponse,
    CallTranscriptResponse,
    CallTurnCreateRequest,
    CallTurnListResponse,
    CallTurnResponse,
    ErrorResponse,
    utc_now,
)
from voiceagent_api.store import store

router = APIRouter()


@router.get(
    "/v1/calls",
    response_model=CallListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_calls(
    auth: AuthContext = Depends(require_scope("calls:read")),
    limit: int | None = None,
    offset: int = 0,
) -> CallListResponse:
    effective_limit, effective_offset = normalize_pagination(limit, offset)
    items, total = store.list_calls_paginated(auth.organization_id, limit=effective_limit, offset=effective_offset)
    return CallListResponse(items=[CallResponse.model_validate(c) for c in items], total=total)


@router.post(
    "/v1/calls",
    response_model=CallResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def create_call(
    payload: CallCreateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("calls:write")),
) -> CallResponse:
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
        return CallResponse.model_validate(cached["response_body"])

    record = store.create_call(
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
    return CallResponse.model_validate(record)


@router.get(
    "/v1/calls/{call_id}",
    response_model=CallResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_call(
    call_id: str,
    auth: AuthContext = Depends(require_scope("calls:read")),
) -> CallResponse:
    record = store.get_call(call_id, auth.organization_id)
    return CallResponse.model_validate(record)


@router.get(
    "/v1/calls/{call_id}/turns",
    response_model=CallTurnListResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def list_call_turns(
    call_id: str,
    auth: AuthContext = Depends(require_scope("calls:read")),
    limit: int | None = None,
    offset: int = 0,
) -> CallTurnListResponse:
    effective_limit, effective_offset = normalize_pagination(limit, offset)
    items, total = store.list_call_turns_paginated(
        call_id, auth.organization_id, limit=effective_limit, offset=effective_offset
    )
    return CallTurnListResponse(items=[CallTurnResponse.model_validate(t) for t in items], total=total)


@router.get(
    "/v1/calls/{call_id}/transcript",
    response_model=CallTranscriptResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_call_transcript(
    call_id: str,
    auth: AuthContext = Depends(require_scope("calls:read")),
) -> CallTranscriptResponse:
    record = store.get_call_transcript(call_id, auth.organization_id)
    return CallTranscriptResponse.model_validate(record)


@router.post(
    "/v1/calls/{call_id}/turns",
    response_model=CallTurnResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def add_call_turn(
    call_id: str,
    payload: CallTurnCreateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("calls:write")),
) -> CallTurnResponse:
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
        return CallTurnResponse.model_validate(cached["response_body"])

    record = store.add_call_turn(
        call_id,
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
    return CallTurnResponse.model_validate(record)


@router.post(
    "/v1/calls/{call_id}/respond",
    response_model=CallTurnResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def respond_to_call(
    call_id: str,
    payload: CallRespondRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("calls:write")),
) -> CallTurnResponse:
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
        return CallTurnResponse.model_validate(cached["response_body"])

    record = store.respond_to_call(
        call_id,
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
    return CallTurnResponse.model_validate(record)


@router.post(
    "/v1/calls/{call_id}/complete",
    response_model=CallResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def complete_call(
    call_id: str,
    payload: CallCompleteRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("calls:write")),
) -> CallResponse:
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
        return CallResponse.model_validate(cached["response_body"])

    record = store.complete_call(
        call_id,
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
    return CallResponse.model_validate(record)


@router.get(
    "/v1/calls/{call_id}/summary",
    response_model=CallSummaryResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_call_summary(
    call_id: str,
    auth: AuthContext = Depends(require_scope("calls:read")),
) -> CallSummaryResponse:
    record = store.get_call_summary(call_id, auth.organization_id)
    return CallSummaryResponse.model_validate(record)
