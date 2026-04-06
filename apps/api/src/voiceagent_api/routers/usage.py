from __future__ import annotations

from fastapi import APIRouter, Depends

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.schemas import (
    ErrorResponse,
    UsageCostResponse,
    UsageSummaryResponse,
)
from voiceagent_api.store import store

router = APIRouter()


@router.get(
    "/v1/usage",
    response_model=UsageSummaryResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def get_usage_summary(
    auth: AuthContext = Depends(require_scope("usage:read")),
) -> UsageSummaryResponse:
    record = store.get_usage_summary(auth.organization_id)
    return UsageSummaryResponse.model_validate(record)


@router.get(
    "/v1/usage/costs",
    response_model=UsageCostResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def get_usage_costs(
    auth: AuthContext = Depends(require_scope("usage:read")),
) -> UsageCostResponse:
    record = store.get_usage_costs(auth.organization_id)
    return UsageCostResponse.model_validate(record)
