from __future__ import annotations

import hashlib
import json
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import httpx

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.config import settings
from voiceagent_api.errors import (
    IdempotencyRequiredError,
    InvalidSignatureError,
    UpstreamServiceError,
    VoiceAgentError,
)
from voiceagent_api.lemonsqueezy import validate_license_key, verify_webhook_signature
from voiceagent_api.schemas import (
    AgentCreateRequest,
    AgentListResponse,
    AgentResponse,
    AgentUpdateRequest,
    AgentVersionListResponse,
    AgentVersionResponse,
    ApiKeyListResponse,
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyDeleteResponse,
    ApiKeyMetadataResponse,
    BillingWebhookResponse,
    BookingCreateRequest,
    BookingListResponse,
    BookingResponse,
    BookingUpdateRequest,
    CallCompleteRequest,
    CallCreateRequest,
    CallRespondRequest,
    CallListResponse,
    CallResponse,
    CallSummaryResponse,
    CallTranscriptResponse,
    CallTurnCreateRequest,
    CallTurnListResponse,
    CallTurnResponse,
    ErrorResponse,
    EventListResponse,
    EventResponse,
    HealthResponse,
    IntegrationConnectRequest,
    IntegrationListResponse,
    IntegrationResponse,
    IntegrationTestResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseDocumentCreateRequest,
    KnowledgeBaseDocumentResponse,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
    LicenseListResponse,
    LicenseResponse,
    LicenseValidateRequest,
    LicenseValidateResponse,
    OrganizationResponse,
    OrganizationUpdateRequest,
    PartnerAccountCreateRequest,
    PartnerAccountListResponse,
    PartnerAccountResponse,
    PartnerResponse,
    PhoneNumberCreateRequest,
    PhoneNumberListResponse,
    PhoneNumberResponse,
    PhoneNumberUpdateRequest,
    PlanListResponse,
    PlanResponse,
    PublishAgentRequest,
    PublishAgentResponse,
    RollbackAgentRequest,
    RollbackAgentResponse,
    ReadyResponse,
    SubscriptionListResponse,
    SubscriptionResponse,
    TemplateInstantiateRequest,
    TemplateListResponse,
    TemplateResponse,
    UsageCostResponse,
    UsageSummaryResponse,
    WebhookCreateRequest,
    WebhookDeliveryProcessResponse,
    WebhookDeliveryListResponse,
    WebhookDeliveryResponse,
    WebhookListResponse,
    WebhookResponse,
    WebhookTestResponse,
    utc_now,
)
from voiceagent_api.store import store


def _trace_id_from_request(request: Request) -> str:
    return request.headers.get("x-trace-id", str(uuid.uuid4()))


def _idempotency_key_from_request(request: Request) -> str | None:
    key = request.headers.get("Idempotency-Key") or request.headers.get("idempotency-key")
    if key is None:
        return None
    key = key.strip()
    return key or None


def _require_idempotency_key(request: Request) -> str:
    key = _idempotency_key_from_request(request)
    if not key:
        raise IdempotencyRequiredError()
    return key


def _idempotency_request_hash(payload: object, *, path: str, method: str) -> str:
    body = jsonable_encoder({"payload": payload, "path": path, "method": method.upper()})
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _apply_pagination(items: list[object], *, limit: int | None, offset: int, max_limit: int = 100) -> tuple[list[object], int]:
    total = len(items)
    if offset < 0:
        offset = 0
    if limit is None:
        limit = total
    else:
        limit = max(0, min(limit, max_limit))
    if offset >= total:
        return [], total
    return items[offset : offset + limit], total


def create_app() -> FastAPI:
    app = FastAPI(title="VoiceAgent API", version="0.1.0")

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/ready", response_model=ReadyResponse)
    async def ready() -> ReadyResponse:
        store.ping()
        return ReadyResponse(status="ready", environment=settings.env)

    @app.get(
        "/v1/organizations/current",
        response_model=OrganizationResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def get_current_organization(
        auth: AuthContext = Depends(require_scope("orgs:read")),
    ) -> OrganizationResponse:
        record = store.get_current_organization(auth.organization_id)
        return OrganizationResponse.model_validate(record)

    @app.patch(
        "/v1/organizations/current",
        response_model=OrganizationResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def update_current_organization(
        payload: OrganizationUpdateRequest,
        auth: AuthContext = Depends(require_scope("orgs:write")),
    ) -> OrganizationResponse:
        record = store.update_organization(payload, organization_id=auth.organization_id, now=utc_now())
        return OrganizationResponse.model_validate(record)

    @app.get(
        "/v1/api-keys",
        response_model=ApiKeyListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def list_api_keys(
        auth: AuthContext = Depends(require_scope("api_keys:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> ApiKeyListResponse:
        raw_items = store.list_api_keys(auth.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [ApiKeyMetadataResponse.model_validate(item) for item in paged]
        return ApiKeyListResponse(items=items, total=total)

    @app.post(
        "/v1/api-keys",
        response_model=ApiKeyCreateResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def create_api_key(
        payload: ApiKeyCreateRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("api_keys:write")),
    ) -> ApiKeyCreateResponse:
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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

        record = store.create_api_key(payload, organization_id=auth.organization_id, now=utc_now())
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

    @app.delete(
        "/v1/api-keys/{key_id}",
        response_model=ApiKeyDeleteResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def delete_api_key(
        key_id: str,
        auth: AuthContext = Depends(require_scope("api_keys:write")),
    ) -> ApiKeyDeleteResponse:
        record = store.delete_api_key(key_id, organization_id=auth.organization_id)
        return ApiKeyDeleteResponse.model_validate(record)

    @app.get(
        "/v1/plans",
        response_model=PlanListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def list_plans(
        _: AuthContext = Depends(require_scope("billing:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> PlanListResponse:
        raw_items = store.list_plans()
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [PlanResponse.model_validate(item) for item in paged]
        return PlanListResponse(items=items, total=total)

    @app.get(
        "/v1/subscriptions",
        response_model=SubscriptionListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def list_subscriptions(
        auth: AuthContext = Depends(require_scope("billing:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> SubscriptionListResponse:
        raw_items = store.list_subscriptions(auth.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [SubscriptionResponse.model_validate(item) for item in paged]
        return SubscriptionListResponse(items=items, total=total)

    @app.get(
        "/v1/licenses",
        response_model=LicenseListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def list_licenses(
        auth: AuthContext = Depends(require_scope("billing:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> LicenseListResponse:
        raw_items = store.list_licenses(auth.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [LicenseResponse.model_validate(item) for item in paged]
        return LicenseListResponse(items=items, total=total)

    @app.post("/v1/billing/lemonsqueezy/webhook", response_model=BillingWebhookResponse)
    async def lemonsqueezy_webhook(request: Request) -> BillingWebhookResponse:
        raw_body = await request.body()
        signature = request.headers.get("X-Signature", "")
        if not verify_webhook_signature(raw_body, signature):
            raise InvalidSignatureError()
        payload = await request.json()
        record = store.process_lemonsqueezy_webhook(
            payload=payload,
            signature_verified=True,
            received_at=utc_now(),
        )
        return BillingWebhookResponse.model_validate(record)

    @app.post(
        "/v1/licenses/validate",
        response_model=LicenseValidateResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    )
    async def validate_license(
        payload: LicenseValidateRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("billing:write")),
    ) -> LicenseValidateResponse:
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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
            result = validate_license_key(
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

    @app.get(
        "/v1/agents",
        response_model=AgentListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def list_agents(
        _: AuthContext = Depends(require_scope("agents:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> AgentListResponse:
        raw_items = store.list_agents(_.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [AgentResponse.model_validate(agent) for agent in paged]
        return AgentListResponse(items=items, total=total)

    @app.post(
        "/v1/agents",
        response_model=AgentResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def create_agent(
        payload: AgentCreateRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("agents:write")),
    ) -> AgentResponse:
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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
            return AgentResponse.model_validate(cached["response_body"])

        record = store.create_agent(payload, organization_id=auth.organization_id, now=utc_now())
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
        return AgentResponse.model_validate(record)

    @app.get(
        "/v1/agents/{agent_id}",
        response_model=AgentResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def get_agent(
        agent_id: str,
        auth: AuthContext = Depends(require_scope("agents:read")),
    ) -> AgentResponse:
        record = store.get_agent(agent_id, auth.organization_id)
        return AgentResponse.model_validate(record)

    @app.patch(
        "/v1/agents/{agent_id}",
        response_model=AgentResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def update_agent(
        agent_id: str,
        payload: AgentUpdateRequest,
        auth: AuthContext = Depends(require_scope("agents:write")),
    ) -> AgentResponse:
        record = store.update_agent(agent_id, payload, organization_id=auth.organization_id, now=utc_now())
        return AgentResponse.model_validate(record)

    @app.get(
        "/v1/agents/{agent_id}/versions",
        response_model=AgentVersionListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def list_agent_versions(
        agent_id: str,
        auth: AuthContext = Depends(require_scope("agents:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> AgentVersionListResponse:
        raw_items = [
            AgentVersionResponse.model_validate(version)
            for version in store.list_versions(agent_id, auth.organization_id)
        ]
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        return AgentVersionListResponse(items=paged, total=total)

    @app.get(
        "/v1/agents/{agent_id}/versions/{version_id}",
        response_model=AgentVersionResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def get_agent_version(
        agent_id: str,
        version_id: str,
        auth: AuthContext = Depends(require_scope("agents:read")),
    ) -> AgentVersionResponse:
        record = store.get_version(agent_id, version_id, auth.organization_id)
        return AgentVersionResponse.model_validate(record)

    @app.get(
        "/v1/templates",
        response_model=TemplateListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def list_templates(
        _: AuthContext = Depends(require_scope("templates:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> TemplateListResponse:
        raw_items = store.list_templates()
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [TemplateResponse.model_validate(item) for item in paged]
        return TemplateListResponse(items=items, total=total)

    @app.post(
        "/v1/templates/{template_id}/instantiate",
        response_model=AgentResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def instantiate_template(
        template_id: str,
        payload: TemplateInstantiateRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("templates:write")),
    ) -> AgentResponse:
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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
            return AgentResponse.model_validate(cached["response_body"])

        record = store.instantiate_template(
            template_id,
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
        return AgentResponse.model_validate(record)

    @app.post(
        "/v1/agents/{agent_id}/publish",
        response_model=PublishAgentResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def publish_agent(
        agent_id: str,
        payload: PublishAgentRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("agents:publish")),
    ) -> PublishAgentResponse:
        trace_id = _trace_id_from_request(request)
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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
            return PublishAgentResponse.model_validate(cached["response_body"])

        record = store.publish_agent(
            agent_id,
            organization_id=auth.organization_id,
            target_environment=payload.target_environment,
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
        return PublishAgentResponse.model_validate(record)

    @app.post(
        "/v1/agents/{agent_id}/rollback",
        response_model=RollbackAgentResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def rollback_agent(
        agent_id: str,
        payload: RollbackAgentRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("agents:publish")),
    ) -> RollbackAgentResponse:
        trace_id = _trace_id_from_request(request)
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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
            return RollbackAgentResponse.model_validate(cached["response_body"])

        record = store.rollback_agent(
            agent_id,
            organization_id=auth.organization_id,
            target_version_id=payload.version_id,
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
        return RollbackAgentResponse.model_validate(record)

    @app.get(
        "/v1/bookings",
        response_model=BookingListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def list_bookings(
        _: AuthContext = Depends(require_scope("bookings:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> BookingListResponse:
        raw_items = store.list_bookings(_.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [BookingResponse.model_validate(booking) for booking in paged]
        return BookingListResponse(items=items, total=total)

    @app.post(
        "/v1/bookings",
        response_model=BookingResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def create_booking(
        payload: BookingCreateRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("bookings:write")),
    ) -> BookingResponse:
        trace_id = _trace_id_from_request(request)
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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

    @app.get(
        "/v1/bookings/{booking_id}",
        response_model=BookingResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def get_booking(
        booking_id: str,
        auth: AuthContext = Depends(require_scope("bookings:read")),
    ) -> BookingResponse:
        record = store.get_booking(booking_id, auth.organization_id)
        return BookingResponse.model_validate(record)

    @app.get(
        "/v1/phone-numbers",
        response_model=PhoneNumberListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def list_phone_numbers(
        _: AuthContext = Depends(require_scope("phone_numbers:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> PhoneNumberListResponse:
        raw_items = store.list_phone_numbers(_.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [PhoneNumberResponse.model_validate(item) for item in paged]
        return PhoneNumberListResponse(items=items, total=total)

    @app.post(
        "/v1/phone-numbers",
        response_model=PhoneNumberResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def create_phone_number(
        payload: PhoneNumberCreateRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("phone_numbers:write")),
    ) -> PhoneNumberResponse:
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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

    @app.patch(
        "/v1/phone-numbers/{number_id}",
        response_model=PhoneNumberResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def update_phone_number(
        number_id: str,
        payload: PhoneNumberUpdateRequest,
        auth: AuthContext = Depends(require_scope("phone_numbers:write")),
    ) -> PhoneNumberResponse:
        record = store.update_phone_number(
            number_id,
            payload,
            organization_id=auth.organization_id,
            now=utc_now(),
        )
        return PhoneNumberResponse.model_validate(record)

    @app.patch(
        "/v1/bookings/{booking_id}",
        response_model=BookingResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def update_booking(
        booking_id: str,
        payload: BookingUpdateRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("bookings:write")),
    ) -> BookingResponse:
        trace_id = _trace_id_from_request(request)
        record = store.update_booking(
            booking_id,
            payload,
            organization_id=auth.organization_id,
            trace_id=trace_id,
            now=utc_now(),
        )
        return BookingResponse.model_validate(record)

    @app.get(
        "/v1/knowledge-bases",
        response_model=KnowledgeBaseListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def list_knowledge_bases(
        _: AuthContext = Depends(require_scope("knowledge_bases:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> KnowledgeBaseListResponse:
        raw_items = store.list_knowledge_bases(_.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [KnowledgeBaseResponse.model_validate(item) for item in paged]
        return KnowledgeBaseListResponse(items=items, total=total)

    @app.post(
        "/v1/knowledge-bases",
        response_model=KnowledgeBaseResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def create_knowledge_base(
        payload: KnowledgeBaseCreateRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("knowledge_bases:write")),
    ) -> KnowledgeBaseResponse:
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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
            return KnowledgeBaseResponse.model_validate(cached["response_body"])

        record = store.create_knowledge_base(payload, organization_id=auth.organization_id, now=utc_now())
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
        return KnowledgeBaseResponse.model_validate(record)

    @app.post(
        "/v1/knowledge-bases/{kb_id}/documents",
        response_model=KnowledgeBaseDocumentResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def add_knowledge_document(
        kb_id: str,
        payload: KnowledgeBaseDocumentCreateRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("knowledge_bases:write")),
    ) -> KnowledgeBaseDocumentResponse:
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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
            return KnowledgeBaseDocumentResponse.model_validate(cached["response_body"])

        record = store.add_knowledge_document(
            kb_id,
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
        return KnowledgeBaseDocumentResponse.model_validate(record)

    @app.get(
        "/v1/integrations",
        response_model=IntegrationListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def list_integrations(
        _: AuthContext = Depends(require_scope("integrations:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> IntegrationListResponse:
        raw_items = store.list_integrations(_.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [IntegrationResponse.model_validate(item) for item in paged]
        return IntegrationListResponse(items=items, total=total)

    @app.post(
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
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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

    @app.post(
        "/v1/integrations/{provider}/test",
        response_model=IntegrationTestResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def test_integration(
        provider: str,
        auth: AuthContext = Depends(require_scope("integrations:write")),
    ) -> IntegrationTestResponse:
        record = store.test_integration(
            provider,
            organization_id=auth.organization_id,
            now=utc_now(),
        )
        return IntegrationTestResponse.model_validate(record)

    @app.get(
        "/v1/usage",
        response_model=UsageSummaryResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def get_usage_summary(
        _: AuthContext = Depends(require_scope("usage:read")),
    ) -> UsageSummaryResponse:
        record = store.get_usage_summary(_.organization_id)
        return UsageSummaryResponse.model_validate(record)

    @app.get(
        "/v1/usage/costs",
        response_model=UsageCostResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def get_usage_costs(
        _: AuthContext = Depends(require_scope("usage:read")),
    ) -> UsageCostResponse:
        record = store.get_usage_costs(_.organization_id)
        return UsageCostResponse.model_validate(record)

    @app.get(
        "/v1/partners/current",
        response_model=PartnerResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def get_current_partner(
        auth: AuthContext = Depends(require_scope("partners:read")),
    ) -> PartnerResponse:
        record = store.get_partner(auth.organization_id)
        return PartnerResponse.model_validate(record)

    @app.get(
        "/v1/partners/current/accounts",
        response_model=PartnerAccountListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def list_partner_accounts(
        auth: AuthContext = Depends(require_scope("partners:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> PartnerAccountListResponse:
        raw_items = store.list_partner_accounts(auth.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [PartnerAccountResponse.model_validate(item) for item in paged]
        return PartnerAccountListResponse(items=items, total=total)

    @app.post(
        "/v1/partners/current/accounts",
        response_model=PartnerAccountResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def create_partner_account(
        payload: PartnerAccountCreateRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("partners:write")),
    ) -> PartnerAccountResponse:
        trace_id = _trace_id_from_request(request)
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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

    @app.get(
        "/v1/calls",
        response_model=CallListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def list_calls(
        _: AuthContext = Depends(require_scope("calls:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> CallListResponse:
        raw_items = store.list_calls(_.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [CallResponse.model_validate(call) for call in paged]
        return CallListResponse(items=items, total=total)

    @app.post(
        "/v1/calls",
        response_model=CallResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def create_call(
        payload: CallCreateRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("calls:write")),
    ) -> CallResponse:
        trace_id = _trace_id_from_request(request)
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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

    @app.get(
        "/v1/calls/{call_id}",
        response_model=CallResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def get_call(
        call_id: str,
        auth: AuthContext = Depends(require_scope("calls:read")),
    ) -> CallResponse:
        record = store.get_call(call_id, auth.organization_id)
        return CallResponse.model_validate(record)

    @app.get(
        "/v1/calls/{call_id}/turns",
        response_model=CallTurnListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def list_call_turns(
        call_id: str,
        auth: AuthContext = Depends(require_scope("calls:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> CallTurnListResponse:
        raw_items = store.list_call_turns(call_id, auth.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [CallTurnResponse.model_validate(turn) for turn in paged]
        return CallTurnListResponse(items=items, total=total)

    @app.get(
        "/v1/calls/{call_id}/transcript",
        response_model=CallTranscriptResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def get_call_transcript(
        call_id: str,
        auth: AuthContext = Depends(require_scope("calls:read")),
    ) -> CallTranscriptResponse:
        record = store.get_call_transcript(call_id, auth.organization_id)
        return CallTranscriptResponse.model_validate(record)

    @app.post(
        "/v1/calls/{call_id}/turns",
        response_model=CallTurnResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def add_call_turn(
        call_id: str,
        payload: CallTurnCreateRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("calls:write")),
    ) -> CallTurnResponse:
        trace_id = _trace_id_from_request(request)
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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

    @app.post(
        "/v1/calls/{call_id}/respond",
        response_model=CallTurnResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def respond_to_call(
        call_id: str,
        payload: CallRespondRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("calls:write")),
    ) -> CallTurnResponse:
        trace_id = _trace_id_from_request(request)
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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

    @app.post(
        "/v1/calls/{call_id}/complete",
        response_model=CallResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def complete_call(
        call_id: str,
        payload: CallCompleteRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("calls:write")),
    ) -> CallResponse:
        trace_id = _trace_id_from_request(request)
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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

    @app.get(
        "/v1/calls/{call_id}/summary",
        response_model=CallSummaryResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def get_call_summary(
        call_id: str,
        auth: AuthContext = Depends(require_scope("calls:read")),
    ) -> CallSummaryResponse:
        record = store.get_call_summary(call_id, auth.organization_id)
        return CallSummaryResponse.model_validate(record)

    @app.get(
        "/v1/events",
        response_model=EventListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def list_events(
        _: AuthContext = Depends(require_scope("events:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> EventListResponse:
        raw_items = store.list_events(_.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [EventResponse.model_validate(event) for event in paged]
        return EventListResponse(items=items, total=total)

    @app.get(
        "/v1/webhooks",
        response_model=WebhookListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def list_webhooks(
        _: AuthContext = Depends(require_scope("webhooks:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> WebhookListResponse:
        raw_items = store.list_webhooks(_.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [WebhookResponse.model_validate(hook) for hook in paged]
        return WebhookListResponse(items=items, total=total)

    @app.delete(
        "/v1/webhooks/{webhook_id}",
        response_model=WebhookResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def delete_webhook(
        webhook_id: str,
        auth: AuthContext = Depends(require_scope("webhooks:write")),
    ) -> WebhookResponse:
        record = store.delete_webhook(webhook_id, organization_id=auth.organization_id, now=utc_now())
        return WebhookResponse.model_validate(record)

    @app.post(
        "/v1/webhooks",
        response_model=WebhookResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def create_webhook(
        payload: WebhookCreateRequest,
        request: Request,
        auth: AuthContext = Depends(require_scope("webhooks:write")),
    ) -> WebhookResponse:
        idempotency_key = _require_idempotency_key(request)
        request_hash = _idempotency_request_hash(
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

    @app.get(
        "/v1/webhooks/{webhook_id}/deliveries",
        response_model=WebhookDeliveryListResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def list_webhook_deliveries(
        webhook_id: str,
        auth: AuthContext = Depends(require_scope("webhooks:read")),
        limit: int | None = None,
        offset: int = 0,
    ) -> WebhookDeliveryListResponse:
        raw_items = store.list_webhook_deliveries(webhook_id, auth.organization_id)
        paged, total = _apply_pagination(raw_items, limit=limit, offset=offset)
        items = [WebhookDeliveryResponse.model_validate(delivery) for delivery in paged]
        return WebhookDeliveryListResponse(items=items, total=total)

    @app.post(
        "/v1/webhooks/deliveries/process",
        response_model=WebhookDeliveryProcessResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    async def process_webhook_deliveries(
        limit: int = 50,
        auth: AuthContext = Depends(require_scope("webhooks:write")),
    ) -> WebhookDeliveryProcessResponse:
        record = store.process_webhook_deliveries(
            organization_id=auth.organization_id,
            now=utc_now(),
            limit=max(1, min(limit, 100)),
        )
        return WebhookDeliveryProcessResponse.model_validate(record)

    @app.post(
        "/v1/webhooks/{webhook_id}/deliveries/{delivery_id}/retry",
        response_model=WebhookDeliveryResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def retry_webhook_delivery(
        webhook_id: str,
        delivery_id: str,
        auth: AuthContext = Depends(require_scope("webhooks:write")),
    ) -> WebhookDeliveryResponse:
        record = store.retry_webhook_delivery(
            webhook_id,
            delivery_id,
            organization_id=auth.organization_id,
            now=utc_now(),
        )
        return WebhookDeliveryResponse.model_validate(record)

    @app.post(
        "/v1/webhooks/{webhook_id}/test",
        response_model=WebhookTestResponse,
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def test_webhook(
        webhook_id: str,
        request: Request,
        auth: AuthContext = Depends(require_scope("webhooks:write")),
    ) -> WebhookTestResponse:
        trace_id = _trace_id_from_request(request)
        record = store.test_webhook(
            webhook_id,
            organization_id=auth.organization_id,
            trace_id=trace_id,
            now=utc_now(),
        )
        return WebhookTestResponse.model_validate(record)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        trace_id = _trace_id_from_request(request)
        body = ErrorResponse(
            error={
                "code": "validation_error",
                "message": "Invalid request payload",
                "category": "validation",
                "trace_id": trace_id,
            }
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(VoiceAgentError)
    async def voiceagent_error_handler(request: Request, exc: VoiceAgentError) -> JSONResponse:
        trace_id = _trace_id_from_request(request)
        body = ErrorResponse(
            error={
                "code": exc.code,
                "message": exc.message,
                "category": exc.category,
                "trace_id": trace_id,
            }
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())

    return app


app = create_app()
