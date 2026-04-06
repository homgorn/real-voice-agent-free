from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.schemas import (
    ErrorResponse,
    WebhookCreateRequest,
    WebhookDeliveryListResponse,
    WebhookDeliveryProcessResponse,
    WebhookDeliveryResponse,
    WebhookListResponse,
    WebhookResponse,
    WebhookTestResponse,
    utc_now,
)
from voiceagent_api.store import store
from voiceagent_api.routers._helpers import (
    trace_id_from_request,
    require_idempotency_key,
    idempotency_request_hash,
)

router = APIRouter()


@router.get(
    "/v1/webhooks",
    response_model=WebhookListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_webhooks(
    auth: AuthContext = Depends(require_scope("webhooks:read")),
    limit: int | None = None,
    offset: int = 0,
) -> WebhookListResponse:
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = store.list_webhooks(auth.organization_id)
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    items = [WebhookResponse.model_validate(hook) for hook in paged]
    return WebhookListResponse(items=items, total=total)


@router.delete(
    "/v1/webhooks/{webhook_id}",
    response_model=WebhookResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def delete_webhook(
    webhook_id: str,
    auth: AuthContext = Depends(require_scope("webhooks:write")),
) -> WebhookResponse:
    record = store.delete_webhook(webhook_id, organization_id=auth.organization_id, now=utc_now())
    return WebhookResponse.model_validate(record)


@router.post(
    "/v1/webhooks",
    response_model=WebhookResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def create_webhook(
    payload: WebhookCreateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("webhooks:write")),
) -> WebhookResponse:
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
        return WebhookResponse.model_validate(cached["response_body"])

    record = store.create_webhook(payload, organization_id=auth.organization_id, now=utc_now())
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
    return WebhookResponse.model_validate(record)


@router.get(
    "/v1/webhooks/{webhook_id}/deliveries",
    response_model=WebhookDeliveryListResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def list_webhook_deliveries(
    webhook_id: str,
    auth: AuthContext = Depends(require_scope("webhooks:read")),
    limit: int | None = None,
    offset: int = 0,
) -> WebhookDeliveryListResponse:
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = store.list_webhook_deliveries(webhook_id, auth.organization_id)
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    items = [WebhookDeliveryResponse.model_validate(delivery) for delivery in paged]
    return WebhookDeliveryListResponse(items=items, total=total)


@router.post(
    "/v1/webhooks/deliveries/process",
    response_model=WebhookDeliveryProcessResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def process_webhook_deliveries(
    limit: int = 50,
    request: Request = None,
    auth: AuthContext = Depends(require_scope("webhooks:write")),
) -> WebhookDeliveryProcessResponse:
    record = store.process_webhook_deliveries(
        organization_id=auth.organization_id,
        now=utc_now(),
        limit=max(1, min(limit, 100)),
    )
    return WebhookDeliveryProcessResponse.model_validate(record)


@router.post(
    "/v1/webhooks/{webhook_id}/deliveries/{delivery_id}/retry",
    response_model=WebhookDeliveryResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def retry_webhook_delivery(
    webhook_id: str,
    delivery_id: str,
    request: Request,
    auth: AuthContext = Depends(require_scope("webhooks:write")),
) -> WebhookDeliveryResponse:
    idempotency_key = require_idempotency_key(request)
    request_hash = idempotency_request_hash(
        {"webhook_id": webhook_id, "delivery_id": delivery_id},
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
        return WebhookDeliveryResponse.model_validate(cached["response_body"])

    record = store.retry_webhook_delivery(
        webhook_id,
        delivery_id,
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
    return WebhookDeliveryResponse.model_validate(record)


@router.post(
    "/v1/webhooks/{webhook_id}/test",
    response_model=WebhookTestResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def test_webhook(
    webhook_id: str,
    request: Request,
    auth: AuthContext = Depends(require_scope("webhooks:write")),
) -> WebhookTestResponse:
    trace_id = trace_id_from_request(request)
    idempotency_key = require_idempotency_key(request)
    request_hash = idempotency_request_hash(
        {"webhook_id": webhook_id},
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
        return WebhookTestResponse.model_validate(cached["response_body"])

    record = store.test_webhook(
        webhook_id,
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
    return WebhookTestResponse.model_validate(record)
