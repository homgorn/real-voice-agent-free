from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Request

from voiceagent_api import lemonsqueezy
from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.errors import InvalidSignatureError, UpstreamServiceError
from voiceagent_api.routers._helpers import (
    idempotency_request_hash,
    require_idempotency_key,
)
from voiceagent_api.schemas import (
    BillingWebhookResponse,
    ErrorResponse,
    LicenseListResponse,
    LicenseResponse,
    LicenseValidateRequest,
    LicenseValidateResponse,
    PlanListResponse,
    PlanResponse,
    SubscriptionListResponse,
    SubscriptionResponse,
    utc_now,
)
from voiceagent_api.store import store

router = APIRouter()


@router.get(
    "/v1/plans",
    response_model=PlanListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_plans(
    _: AuthContext = Depends(require_scope("billing:read")),
    limit: int | None = None,
    offset: int = 0,
) -> PlanListResponse:
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = store.list_plans()
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    items = [PlanResponse.model_validate(item) for item in paged]
    return PlanListResponse(items=items, total=total)


@router.get(
    "/v1/subscriptions",
    response_model=SubscriptionListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_subscriptions(
    auth: AuthContext = Depends(require_scope("billing:read")),
    limit: int | None = None,
    offset: int = 0,
) -> SubscriptionListResponse:
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = store.list_subscriptions(auth.organization_id)
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    items = [SubscriptionResponse.model_validate(item) for item in paged]
    return SubscriptionListResponse(items=items, total=total)


@router.get(
    "/v1/licenses",
    response_model=LicenseListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_licenses(
    auth: AuthContext = Depends(require_scope("billing:read")),
    limit: int | None = None,
    offset: int = 0,
) -> LicenseListResponse:
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = store.list_licenses(auth.organization_id)
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    items = [LicenseResponse.model_validate(item) for item in paged]
    return LicenseListResponse(items=items, total=total)


@router.post("/v1/billing/lemonsqueezy/webhook", response_model=BillingWebhookResponse)
async def lemonsqueezy_webhook(request: Request) -> BillingWebhookResponse:
    raw_body = await request.body()
    signature = request.headers.get("X-Signature", "")
    if not lemonsqueezy.verify_webhook_signature(raw_body, signature):
        raise InvalidSignatureError()
    payload = await request.json()
    record = store.process_lemonsqueezy_webhook(
        payload=payload,
        signature_verified=True,
        received_at=utc_now(),
    )
    return BillingWebhookResponse.model_validate(record)


@router.post(
    "/v1/licenses/validate",
    response_model=LicenseValidateResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def validate_license(
    payload: LicenseValidateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("billing:write")),
) -> LicenseValidateResponse:
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
        return LicenseValidateResponse.model_validate(cached["response_body"])

    try:
        result = lemonsqueezy.validate_license_key(
            license_key=payload.license_key,
            instance_name=payload.instance_name,
            instance_id=payload.instance_id,
        )
    except httpx.HTTPStatusError as exc:
        raise UpstreamServiceError(f"Lemon Squeezy returned HTTP {exc.response.status_code}", status_code=502) from exc
    except httpx.HTTPError as exc:
        raise UpstreamServiceError(f"Lemon Squeezy request failed: {exc}") from exc
    store.record_license_validation(
        organization_id=auth.organization_id,
        validation_response=result,
        received_at=utc_now(),
    )
    store.store_idempotent_response(
        organization_id=auth.organization_id,
        key=idempotency_key,
        method=request.method,
        path=request.url.path,
        request_hash=request_hash,
        response_body=result,
        response_code=200,
        created_at=utc_now(),
    )
    return LicenseValidateResponse.model_validate(result)
