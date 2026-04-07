from __future__ import annotations

from fastapi import APIRouter, Depends

from voiceagent_api.auth import AuthContext, require_scope
from voiceagent_api.schemas import DashboardOverviewResponse, ErrorResponse
from voiceagent_api.store import store

router = APIRouter()


@router.get(
    "/v1/dashboard/overview",
    response_model=DashboardOverviewResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def get_dashboard_overview(
    auth: AuthContext = Depends(require_scope("usage:read")),
) -> DashboardOverviewResponse:
    record = store.get_dashboard_overview(auth.organization_id)
    return DashboardOverviewResponse.model_validate(record)
