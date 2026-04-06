from __future__ import annotations

from fastapi import APIRouter, Depends

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.schemas import (
    ErrorResponse,
    OrganizationResponse,
    OrganizationUpdateRequest,
    utc_now,
)
from voiceagent_api.store import store

router = APIRouter()


@router.get(
    "/v1/organizations/current",
    response_model=OrganizationResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def get_current_organization(
    auth: AuthContext = Depends(require_scope("orgs:read")),
) -> OrganizationResponse:
    record = store.get_current_organization(auth.organization_id)
    return OrganizationResponse.model_validate(record)


@router.patch(
    "/v1/organizations/current",
    response_model=OrganizationResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def update_current_organization(
    payload: OrganizationUpdateRequest,
    auth: AuthContext = Depends(require_scope("orgs:write")),
) -> OrganizationResponse:
    record = store.update_organization(
        payload, organization_id=auth.organization_id, now=utc_now()
    )
    return OrganizationResponse.model_validate(record)
