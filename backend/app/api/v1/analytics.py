"""Agent 63 - Phase 13/14: Analytics API Endpoints
Provides:
1. Popular-questions aggregation endpoint (Phase 13)
2. Analytical query result export endpoint (Phase 14)
3. Deterministic official report verification endpoint (Phase 14)

Security invariants:
- All endpoints require authentication (JWT).
- Export re-authorizes the requesting principal on every request (fail-closed).
- Export accepts ONLY trusted request_id references (zero client SQL, tables, or rows).
- CSV formula injection mitigated.
- Verification uses deterministic comparison with ZERO LLM calls.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from backend.app.core.errors import AuthorizationError
from backend.app.core.logging import get_logger
from backend.app.dependencies.auth import get_current_principal
from backend.app.schemas.export import (
    ExportRequest,
    VerificationRequest,
    VerificationResult,
)
from backend.app.schemas.principal import AuthenticatedPrincipal
from backend.app.schemas.query_log import PopularQuestion
from backend.app.services.export_service import (
    ExportService,
    get_export_service,
)
from backend.app.services.query_log_service import (
    QueryLoggingService,
    get_query_log_service,
)
from backend.app.services.verification_service import (
    VerificationService,
    get_verification_service,
)

logger = get_logger("agent63.api.analytics")

router = APIRouter(prefix="/analytics", tags=["Usage Analytics & Export"])


@router.get(
    "/popular-questions",
    response_model=List[PopularQuestion],
    status_code=status.HTTP_200_OK,
    summary="Popular analytical patterns",
    description=(
        "Returns the most frequently queried analytical patterns visible to the current user. "
        "Results are aggregated usage patterns. No individual user activity is exposed. "
        "Patterns are filtered to metrics the authenticated principal is authorized to access. "
        "Returns an empty list if no usage data is available within the configured time window."
    ),
)
def get_popular_questions(
    limit: int = Query(
        default=10,
        ge=1,
        le=20,
        description="Maximum number of popular patterns to return (1–20).",
    ),
    window_hours: Optional[int] = Query(
        default=None,
        ge=1,
        le=720,
        description="Aggregation time window in hours (1–720). Defaults to server-configured window.",
    ),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    log_service: QueryLoggingService = Depends(get_query_log_service),
) -> List[PopularQuestion]:
    """
    Returns aggregated popular analytical patterns for the authenticated principal.
    Privacy note: individual users and query contents are never revealed.
    """
    logger.debug(
        f"Popular questions request: user='{principal.username}' roles={principal.roles} "
        f"limit={limit} window_hours={window_hours}"
    )

    popular = log_service.get_popular_questions(
        principal=principal,
        limit=limit,
        window_hours=window_hours,
    )

    logger.debug(
        f"Popular questions returned {len(popular)} patterns for user='{principal.username}'"
    )
    return popular


@router.post(
    "/export",
    summary="Export analytical query result",
    description=(
        "Exports an already-executed, validated analytical result as CSV or JSON. "
        "Strictly server-side: references an authorized request_id. "
        "Re-authorizes principal on every request (fail-closed). "
        "Applies CSV formula injection defense and preserves distinct NULLs."
    ),
)
def export_analytical_result(
    payload: ExportRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    export_service: ExportService = Depends(get_export_service),
) -> Response:
    """
    Exports an authorized analytical result.
    Enforces re-authorization, size ceilings, and format-specific sanitization.
    """
    logger.info(
        f"Export requested: user='{principal.username}' request_id='{payload.request_id}' "
        f"format='{payload.format.value}'"
    )

    try:
        encoded_bytes, media_type, filename = export_service.export_result(
            request_id=payload.request_id,
            export_format=payload.format,
            principal=principal,
        )
    except AuthorizationError:
        raise
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower() or "expired" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return Response(
        content=encoded_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post(
    "/verify",
    response_model=VerificationResult,
    status_code=status.HTTP_200_OK,
    summary="Official report verification",
    description=(
        "Performs deterministic verification comparing an analytical query result against "
        "an authoritative registered institutional report or KPI benchmark. "
        "Zero LLM calls. Re-authorizes principal before execution."
    ),
)
def verify_analytical_result(
    payload: VerificationRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    verification_service: VerificationService = Depends(get_verification_service),
) -> VerificationResult:
    """
    Deterministically reconciles analytical calculation against registered institutional document/KPI.
    """
    logger.info(
        f"Verification requested: user='{principal.username}' request_id='{payload.request_id}'"
    )

    try:
        return verification_service.verify_result(
            payload=payload,
            principal=principal,
        )
    except AuthorizationError:
        raise
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower() or "expired" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
