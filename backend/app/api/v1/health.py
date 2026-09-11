"""
Agent 63 – Health & Readiness Endpoints
Provides machine-readable liveness and dependency readiness probes.
"""

from fastapi import APIRouter, Depends, status
from backend.app.core.config import settings
from backend.app.dependencies.common import get_database_service, get_schema_registry
from backend.app.schemas.health import DependenciesStatus, HealthResponse, ReadinessResponse
from backend.app.services.database import CollegeDatabaseService
from backend.app.services.schema_registry import SchemaRegistryService

router = APIRouter(tags=["Health & Monitoring"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Liveness Probe",
    description="Basic service liveness check. Always returns 'ok' if backend runtime is operational, regardless of database status."
)
async def check_liveness() -> HealthResponse:
    """Liveness probe indicating application process is running."""
    return HealthResponse(
        status="ok",
        service="agent63-backend",
        version=settings.APP_VERSION,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Readiness Probe",
    description="Detailed readiness check distinguishing application runtime from college database and schema registry state."
)
async def check_readiness(
    registry: SchemaRegistryService = Depends(get_schema_registry),
    db: CollegeDatabaseService = Depends(get_database_service),
) -> ReadinessResponse:
    """
    Evaluates backend dependency readiness.
    Distinguishes operational application foundation from unconfigured college database.
    """
    registry_ready = registry.is_ready
    db_status = db.get_status()

    # Determine overall status:
    # If registry is available but database is unconfigured (Phase 2 state), service is functional but 'degraded'
    if not registry_ready:
        overall_status = "degraded"
    elif db_status == "not_configured":
        overall_status = "degraded"
    else:
        overall_status = "ready"

    return ReadinessResponse(
        status=overall_status,
        service="agent63-backend",
        version=settings.APP_VERSION,
        dependencies=DependenciesStatus(
            schema_registry="ready" if registry_ready else "unavailable",
            college_database=db_status,
            schema_registry_objects=registry.get_object_count() if registry_ready else None,
            database_host=settings.COLLEGE_DB_HOST if settings.COLLEGE_DB_HOST else None,
        ),
    )
