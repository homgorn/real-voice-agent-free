from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.schemas import (
    AgentCreateRequest,
    AgentListResponse,
    AgentResponse,
    AgentUpdateRequest,
    AgentVersionListResponse,
    AgentVersionResponse,
    ErrorResponse,
    PublishAgentRequest,
    PublishAgentResponse,
    RollbackAgentRequest,
    RollbackAgentResponse,
    TemplateInstantiateRequest,
    TemplateListResponse,
    TemplateResponse,
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
    "/v1/agents",
    response_model=AgentListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_agents(
    auth: AuthContext = Depends(require_scope("agents:read")),
    limit: int | None = None,
    offset: int = 0,
) -> AgentListResponse:
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = store.list_agents(auth.organization_id)
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    items = [AgentResponse.model_validate(agent) for agent in paged]
    return AgentListResponse(items=items, total=total)


@router.post(
    "/v1/agents",
    response_model=AgentResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def create_agent(
    payload: AgentCreateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("agents:write")),
) -> AgentResponse:
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


@router.get(
    "/v1/agents/{agent_id}",
    response_model=AgentResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_agent(
    agent_id: str,
    auth: AuthContext = Depends(require_scope("agents:read")),
) -> AgentResponse:
    record = store.get_agent(agent_id, auth.organization_id)
    return AgentResponse.model_validate(record)


@router.patch(
    "/v1/agents/{agent_id}",
    response_model=AgentResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def update_agent(
    agent_id: str,
    payload: AgentUpdateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("agents:write")),
) -> AgentResponse:
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
        return AgentResponse.model_validate(cached["response_body"])

    record = store.update_agent(agent_id, payload, organization_id=auth.organization_id, now=utc_now())
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


@router.get(
    "/v1/agents/{agent_id}/versions",
    response_model=AgentVersionListResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def list_agent_versions(
    agent_id: str,
    auth: AuthContext = Depends(require_scope("agents:read")),
    limit: int | None = None,
    offset: int = 0,
) -> AgentVersionListResponse:
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = [
        AgentVersionResponse.model_validate(version) for version in store.list_versions(agent_id, auth.organization_id)
    ]
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    return AgentVersionListResponse(items=paged, total=total)


@router.get(
    "/v1/agents/{agent_id}/versions/{version_id}",
    response_model=AgentVersionResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_agent_version(
    agent_id: str,
    version_id: str,
    auth: AuthContext = Depends(require_scope("agents:read")),
) -> AgentVersionResponse:
    record = store.get_version(agent_id, version_id, auth.organization_id)
    return AgentVersionResponse.model_validate(record)


@router.post(
    "/v1/agents/{agent_id}/publish",
    response_model=PublishAgentResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def publish_agent(
    agent_id: str,
    payload: PublishAgentRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("agents:publish")),
) -> PublishAgentResponse:
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


@router.post(
    "/v1/agents/{agent_id}/rollback",
    response_model=RollbackAgentResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def rollback_agent(
    agent_id: str,
    payload: RollbackAgentRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("agents:publish")),
) -> RollbackAgentResponse:
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


@router.get(
    "/v1/templates",
    response_model=TemplateListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_templates(
    auth: AuthContext = Depends(require_scope("templates:read")),
    limit: int | None = None,
    offset: int = 0,
) -> TemplateListResponse:
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = store.list_templates()
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    items = [TemplateResponse.model_validate(item) for item in paged]
    return TemplateListResponse(items=items, total=total)


@router.post(
    "/v1/templates/{template_id}/instantiate",
    response_model=AgentResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def instantiate_template(
    template_id: str,
    payload: TemplateInstantiateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("templates:write")),
) -> AgentResponse:
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
