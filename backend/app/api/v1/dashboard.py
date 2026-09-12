"""Agent 63 - Phase 12: Role-Based Dashboard API Endpoints
Exposes REST endpoints for catalog discovery, dashboard retrieval, manual refresh,
and scheduled refresh configuration.

CRITICAL SECURITY INVARIANTS:
1. All endpoints require authentication via Bearer token (get_current_principal).
2. Role and scope are derived strictly from the AuthenticatedPrincipal.
3. No frontend role/scope parameter is trusted.
4. No raw SQL is accepted or returned.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.core.errors import AuthorizationError
from backend.app.core.logging import get_logger
from backend.app.dependencies.auth import get_current_principal
from backend.app.schemas.dashboard import (
    DashboardCatalogResponse,
    DashboardResponse,
    DashboardScheduleItem,
    DashboardScheduleRequest,
)
from backend.app.schemas.principal import AuthenticatedPrincipal
from backend.app.services.dashboard_scheduler import (
    DashboardSchedulerService,
    get_dashboard_scheduler_service,
)
from backend.app.services.dashboard_service import (
    DashboardService,
    get_dashboard_service,
)

logger = get_logger("agent63.api.dashboard")

router = APIRouter(prefix="/dashboard", tags=["Role-Based Dashboards"])


@router.get(
    "/catalog",
    response_model=DashboardCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="List available dashboards for the authenticated principal",
    description="Returns server-controlled dashboards matching the authenticated user's authorized institutional roles.",
)
def get_dashboard_catalog(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> DashboardCatalogResponse:
    """Returns the catalog of authorized dashboards for the caller."""
    return dashboard_service.get_catalog(principal)


@router.get(
    "/schedules",
    response_model=List[DashboardScheduleItem],
    status_code=status.HTTP_200_OK,
    summary="List active refresh schedules for the current user",
    description="Returns all active scheduled refresh jobs configured by the current authenticated principal.",
)
def list_dashboard_schedules(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    scheduler_service: DashboardSchedulerService = Depends(get_dashboard_scheduler_service),
) -> List[DashboardScheduleItem]:
    """Lists current user's active refresh schedules."""
    return scheduler_service.list_schedules(principal)


@router.post(
    "/schedules",
    response_model=DashboardScheduleItem,
    status_code=status.HTTP_201_CREATED,
    summary="Configure scheduled refresh for a dashboard",
    description="Registers an hourly or daily scheduled refresh job for an authorized institutional dashboard.",
)
def create_dashboard_schedule(
    payload: DashboardScheduleRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    scheduler_service: DashboardSchedulerService = Depends(get_dashboard_scheduler_service),
) -> DashboardScheduleItem:
    """Creates a new scheduled refresh job."""
    try:
        return scheduler_service.create_schedule(
            principal=principal,
            dashboard_id=payload.dashboard_id,
            interval_minutes=payload.interval_minutes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/schedules/{schedule_id}",
    status_code=status.HTTP_200_OK,
    summary="Cancel a scheduled dashboard refresh",
    description="Deactivates and removes an existing dashboard refresh schedule owned by the user.",
)
def cancel_dashboard_schedule(
    schedule_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    scheduler_service: DashboardSchedulerService = Depends(get_dashboard_scheduler_service),
) -> Dict[str, Any]:
    """Cancels a scheduled refresh job."""
    success = scheduler_service.cancel_schedule(schedule_id, principal)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found.",
        )
    return {"status": "CANCELLED", "schedule_id": schedule_id}


@router.get(
    "/{dashboard_id}",
    response_model=DashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve and execute role-based dashboard",
    description="Resolves server-controlled widgets, verifies metric authorization, executes analytical queries safely, and returns visualization and anomaly assessments.",
)
def get_dashboard(
    dashboard_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    """Loads an authorized role-based dashboard."""
    return dashboard_service.get_dashboard(
        dashboard_id=dashboard_id,
        principal=principal,
        force_refresh=False,
    )


@router.post(
    "/{dashboard_id}/refresh",
    response_model=DashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Manually refresh role-based dashboard data",
    description="Forces re-execution of all authorized dashboard widgets through the analytical pipeline, bypassing the cache.",
)
def refresh_dashboard(
    dashboard_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    """Forces manual refresh of dashboard data."""
    return dashboard_service.get_dashboard(
        dashboard_id=dashboard_id,
        principal=principal,
        force_refresh=True,
    )
