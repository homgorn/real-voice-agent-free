from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.routers._helpers import (
    idempotency_request_hash,
    require_idempotency_key,
)
from voiceagent_api.schemas import (
    ErrorResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseDocumentCreateRequest,
    KnowledgeBaseDocumentResponse,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
    utc_now,
)
from voiceagent_api.store import store

router = APIRouter()


@router.get(
    "/v1/knowledge-bases",
    response_model=KnowledgeBaseListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_knowledge_bases(
    auth: AuthContext = Depends(require_scope("knowledge_bases:read")),
    limit: int | None = None,
    offset: int = 0,
) -> KnowledgeBaseListResponse:
    from voiceagent_api.routers._helpers import apply_pagination

    raw_items = store.list_knowledge_bases(auth.organization_id)
    paged, total = apply_pagination(raw_items, limit=limit, offset=offset)
    items = [KnowledgeBaseResponse.model_validate(item) for item in paged]
    return KnowledgeBaseListResponse(items=items, total=total)


@router.post(
    "/v1/knowledge-bases",
    response_model=KnowledgeBaseResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def create_knowledge_base(
    payload: KnowledgeBaseCreateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("knowledge_bases:write")),
) -> KnowledgeBaseResponse:
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
        return KnowledgeBaseResponse.model_validate(cached["response_body"])

    record = store.create_knowledge_base(
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
    return KnowledgeBaseResponse.model_validate(record)


@router.post(
    "/v1/knowledge-bases/{kb_id}/documents",
    response_model=KnowledgeBaseDocumentResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def add_knowledge_document(
    kb_id: str,
    payload: KnowledgeBaseDocumentCreateRequest,
    request: Request,
    auth: AuthContext = Depends(require_scope("knowledge_bases:write")),
) -> KnowledgeBaseDocumentResponse:
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
