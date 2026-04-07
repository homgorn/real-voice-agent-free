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
    BookingCreateRequest,
    BookingListResponse,
    BookingResponse,
    BookingUpdateRequest,
    ErrorResponse,
    utc_now,
)
from voiceagent_api.store import store

router = APIRouter()


@router.get(
    "/v1/bookings",
    response_model=BookingListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_bookings(
    auth: AuthContext = Depends(require_scope("bookings:read")),
    limit: int | None = None,
    offset: int = 0,
) -> BookingListResponse:
    effective_limit, effective_offset = normalize_pagination(limit, offset)
    items, total = store.list_bookings_paginated(auth.organization_id, limit=effective_limit, offset=effective_offset)
    return BookingListResponse(items=[BookingResponse.model_validate(b) for b in items], total=total)


@router.post(
    "/v1/bookings",
    response_model=BookingResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def create_booking(
    payload: BookingCreateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("bookings:write")),
) -> BookingResponse:
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
        return BookingResponse.model_validate(cached["response_body"])

    record = store.create_booking(
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
    return BookingResponse.model_validate(record)


@router.get(
    "/v1/bookings/{booking_id}",
    response_model=BookingResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_booking(
    booking_id: str,
    auth: AuthContext = Depends(require_scope("bookings:read")),
) -> BookingResponse:
    record = store.get_booking(booking_id, auth.organization_id)
    return BookingResponse.model_validate(record)


@router.patch(
    "/v1/bookings/{booking_id}",
    response_model=BookingResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def update_booking(
    booking_id: str,
    payload: BookingUpdateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("bookings:write")),
) -> BookingResponse:
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
        return BookingResponse.model_validate(cached["response_body"])

    record = store.update_booking(
        booking_id,
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
    return BookingResponse.model_validate(record)
