"""Agent 63 - Phase 8/13: Agent Query API Endpoint
Accepts natural language analytical questions, orchestrates intent interpretation,
deterministic SQL compilation, AST safety validation, and safe read-only database execution.
Phase 13: Integrates QueryLoggingService for bounded, privacy-safe analytical event logging.
"""

import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, status

from backend.app.core.config import settings
from backend.app.core.errors import AuthorizationError, DatabaseNotConfiguredError
from backend.app.core.logging import get_logger, request_id_ctx_var
from backend.app.dependencies.auth import get_current_principal
from backend.app.schemas.conversation_context import ConversationContext
from backend.app.schemas.intent import IntentRequest, IntentType, IntentValidationStatus
from backend.app.schemas.principal import AuthenticatedPrincipal
from backend.app.schemas.query_log import QueryLogEvent, QueryLogEventType, QueryLogStatus
from backend.app.schemas.query_result import (
    AgentQueryRequest,
    AgentQueryResponse,
    QueryResult,
    QueryResultStatus,
)
from backend.app.services.conversation_store import (
    ConversationContextStore,
    get_conversation_store,
)
from backend.app.services.execution_service import execution_service
from backend.app.services.intent_service import IntentService, get_intent_service
from backend.app.services.query_log_service import QueryLoggingService, get_query_log_service
from backend.app.services.sql_compiler import SQLCompiler, get_sql_compiler
from backend.app.services.sql_validator import SQLValidator, get_sql_validator

from backend.app.services.visualization_service import (
    VisualizationService,
    get_visualization_service,
)
from backend.app.services.anomaly_service import (
    AnomalyDetectionService,
    get_anomaly_service,
)
from backend.app.services.export_artifact_store import (
    ExportArtifact,
    get_export_artifact_store,
)

logger = get_logger("agent63.api.agent")


def _safe_log_event(
    log_service: QueryLoggingService,
    event: QueryLogEvent,
) -> None:
    """Wrapper ensuring logging failures are never propagated to callers (fail-open)."""
    try:
        log_service.log_event(event)
    except Exception as e:
        logger.warning(f"Query log event emit failed (non-fatal): {e}")

router = APIRouter(prefix="/agent", tags=["Agent Query Execution"])


@router.delete(
    "/conversation/{conversation_id}",
    status_code=status.HTTP_200_OK,
    summary="Reset or clear conversation context",
    description="Clears an active conversation session if owned by the current authenticated principal.",
)
def reset_conversation(
    conversation_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    conversation_store: ConversationContextStore = Depends(get_conversation_store),
) -> Dict[str, Any]:
    cleared = conversation_store.clear_context(conversation_id, principal)
    return {"status": "CLEARED", "cleared": cleared, "conversation_id": conversation_id}


@router.post(
    "/query",
    response_model=AgentQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="End-to-end analytical query execution",
    description=(
        "Translates natural language to authorized StructuredIntent, compiles deterministic SQL, "
        "validates AST safety, and executes safely against the read-only institutional database. "
        "Supports multi-turn conversational context with strict per-turn re-authorization."
    ),
)
def execute_agent_query(
    payload: AgentQueryRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    intent_service: IntentService = Depends(get_intent_service),
    sql_compiler: SQLCompiler = Depends(get_sql_compiler),
    sql_validator: SQLValidator = Depends(get_sql_validator),
    visualization_service: VisualizationService = Depends(get_visualization_service),
    anomaly_service: AnomalyDetectionService = Depends(get_anomaly_service),
    conversation_store: ConversationContextStore = Depends(get_conversation_store),
    log_service: QueryLoggingService = Depends(get_query_log_service),
) -> AgentQueryResponse:
    """Orchestrates end-to-end natural language query execution with defense-in-depth."""
    req_id = request_id_ctx_var.get()
    _query_start_time = time.monotonic()

    # Step 0: Resolve & Verify Conversation Context
    context: Optional[ConversationContext] = None
    is_follow_up = False

    if payload.conversation_id:
        context = conversation_store.get_context(payload.conversation_id, principal)
        if context:
            active_conv_id = payload.conversation_id
            is_follow_up = True
            logger.info(
                f"Follow-up query detected: conv_id='{active_conv_id}' "
                f"user='{principal.username}' turn={context.turn_count + 1}"
            )
        else:
            active_conv_id = str(uuid.uuid4())
            logger.info(
                f"Provided conversation_id '{payload.conversation_id}' expired or not found for user; "
                f"initialized new conversation context '{active_conv_id}'."
            )
    else:
        active_conv_id = str(uuid.uuid4())

    # Step 1: Natural Language -> StructuredIntent (with passive prior context)
    intent_req = IntentRequest(message=payload.prompt)
    intent_response = intent_service.interpret_intent(
        request=intent_req,
        principal=principal,
        request_id=req_id,
        conversation_context=context,
    )

    if intent_response.status == IntentValidationStatus.REJECTED:
        # If rejected for authorization/scope boundaries, return HTTP 403 Forbidden
        msg = intent_response.message or "Request is not authorized for the current user role or scope."
        err_code = "SCOPE_OUT_OF_BOUNDS" if "scope" in msg.lower() or "hod" in msg.lower() else "AUTHORIZATION_DENIED"
        # Phase 13: Log safe authorization failure event (AFTER rejection decision)
        _safe_log_event(log_service, QueryLogEvent(
            request_id=req_id,
            user_id=principal.user_id,
            role=principal.roles[0] if principal.roles else None,
            scope_type=principal.scoped_roles[0].scope_type.value if principal.scoped_roles else None,
            scope_id=principal.scoped_roles[0].scope_id if principal.scoped_roles else None,
            metric_id=(
                intent_response.intent.metric_id
                if intent_response.intent else None
            ),
            event_type=QueryLogEventType.FOLLOW_UP_QUERY if is_follow_up else QueryLogEventType.MANUAL_QUERY,
            status=QueryLogStatus.UNAUTHORIZED,
            error_category=err_code,
            execution_time_ms=round((time.monotonic() - _query_start_time) * 1000, 2),
            is_follow_up=is_follow_up,
        ))
        err = AuthorizationError(message=msg)
        err.code = err_code
        raise err

    if intent_response.status != IntentValidationStatus.VALID or not intent_response.intent:
        # Phase 13: Log intent resolution failure (safe category only)
        _safe_log_event(log_service, QueryLogEvent(
            request_id=req_id,
            user_id=principal.user_id,
            role=principal.roles[0] if principal.roles else None,
            scope_type=principal.scoped_roles[0].scope_type.value if principal.scoped_roles else None,
            scope_id=principal.scoped_roles[0].scope_id if principal.scoped_roles else None,
            metric_id=(
                intent_response.intent.metric_id
                if intent_response.intent and hasattr(intent_response.intent, 'metric_id') else None
            ),
            event_type=QueryLogEventType.FOLLOW_UP_QUERY if is_follow_up else QueryLogEventType.MANUAL_QUERY,
            status=QueryLogStatus.INTENT_UNRESOLVED,
            error_category="INTENT_VALIDATION_FAILED",
            execution_time_ms=round((time.monotonic() - _query_start_time) * 1000, 2),
            is_follow_up=is_follow_up,
        ))
        return AgentQueryResponse(
            intent=intent_response.intent.model_dump() if intent_response.intent else None,
            sql_artifact=None,
            result=None,
            execution_metadata=None,
            dry_run=payload.dry_run,
            message=intent_response.message or "Query intent could not be validated for analytical execution.",
            request_id=req_id,
            conversation_id=active_conv_id,
            is_follow_up=is_follow_up,
            clarification_questions=intent_response.clarification_questions,
        )

    # Step 2: StructuredIntent -> Safe Parameterized SQLArtifact
    raw_artifact = sql_compiler.compile(
        intent=intent_response.intent,
        principal=principal,
        request_id=req_id,
    )

    # Step 3: AST Safety Validation
    validated_artifact = sql_validator.validate_artifact(raw_artifact)

    is_student_list = (intent_response.intent.intent_type == IntentType.STUDENT_LIST)
    is_student_user = principal.has_role("STUDENT") and not principal.has_any_role(
        "PRINCIPAL", "HOD", "DEAN", "IQAC"
    )
    is_hod_user = principal.has_role("HOD") and not principal.has_any_role(
        "PRINCIPAL", "IQAC", "DEAN", "CAMPUS_ADMIN"
    )

    hod_dept_code = ""
    scope_info: Dict[str, Any] = {}
    if is_hod_user:
        from backend.app.services.identity_resolution import get_identity_resolution_service
        id_svc = get_identity_resolution_service()
        hod_dept = id_svc.resolve_hod_department(principal)
        if hod_dept:
            dept_id, hod_dept_code, dept_name = hod_dept
        else:
            hod_scopes = principal.get_scopes_for_role("HOD")
            dept_id = hod_scopes[0].scope_id if hod_scopes else None
            if dept_id:
                from backend.app.services.sql_compiler import normalize_department_scope
                _, hod_dept_code = normalize_department_scope(dept_id)
            else:
                dept_id = None
                hod_dept_code = "UNKNOWN"
        scope_info = {
            "scope_type": "DEPARTMENT",
            "scope_id": dept_id,
            "display": f"HOD / {hod_dept_code} Department",
        }
    elif is_student_user or (intent_response.intent.filters and intent_response.intent.filters.get("student_id") == "SELF"):
        scope_info = {
            "scope_type": "SELF",
            "scope_id": principal.person_id or (principal.scoped_roles[0].scope_id if principal.scoped_roles else None),
            "display": "Student SELF",
        }
    elif principal.has_any_role("PRINCIPAL", "IQAC", "MANAGEMENT"):
        scope_info = {
            "scope_type": "INSTITUTION",
            "scope_id": None,
            "display": "Institutional",
        }
    elif principal.scoped_roles:
        sr = principal.scoped_roles[0]
        scope_info = {
            "scope_type": sr.scope_type.value,
            "scope_id": sr.scope_id,
            "display": f"{sr.scope_type.value.capitalize()}" + (f" ({sr.scope_id})" if sr.scope_id else ""),
        }

    # Enrich scope display for comparison queries across multiple departments
    comp_label = ""
    dept_filters = (intent_response.intent.filters or {}).get("department")
    if intent_response.intent.intent_type == IntentType.COMPARISON_QUERY or (
        isinstance(dept_filters, list) and len(dept_filters) >= 2
    ):
        comp_label = " vs ".join(str(d) for d in dept_filters) if isinstance(dept_filters, list) else ""
        if comp_label:
            if scope_info.get("scope_type") == "INSTITUTION":
                scope_info["display"] = f"Institutional ({comp_label})"
            elif scope_info.get("display"):
                scope_info["display"] = f"{scope_info['display']} ({comp_label})"

    # Step 4: Check if dry-run requested
    if payload.dry_run:
        logger.info("Dry-run requested: skipping database execution.")
        if is_student_list:
            meta = (
                (f"HOD / {hod_dept_code} Department Student Records", "Department student-level record retrieval")
                if is_hod_user
                else ("Authorized Student Records", "Student-level record retrieval")
            )
        else:
            meta = visualization_service._get_metric_meta(intent_response.intent.metric_id)
            if comp_label:
                meta = (f"{meta[0]} ({comp_label})", meta[1], meta[2])

        # Update Conversation Context for dry-run execution
        new_turn = (context.turn_count + 1) if context else 1
        if new_turn <= settings.CONVERSATION_MAX_TURNS:
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=settings.CONVERSATION_CONTEXT_TTL_SECONDS
            )
            updated_ctx = ConversationContext(
                conversation_id=active_conv_id,
                user_id=principal.user_id,
                last_metric_id=intent_response.intent.metric_id,
                last_intent_type=intent_response.intent.intent_type,
                last_dimensions=intent_response.intent.dimensions,
                last_filters=intent_response.intent.filters,
                last_time_context=intent_response.intent.time_context,
                last_metric_display_name=meta[0],
                turn_count=new_turn,
                created_at=context.created_at if context else datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                expires_at=expires_at,
            )
            conversation_store.save_context(updated_ctx)

        # Phase 13: Log dry-run event (no execution, no rows)
        _filter_keys = (
            list(intent_response.intent.student_filters.keys())
            if is_student_list and intent_response.intent.student_filters
            else list(intent_response.intent.filters.keys()) if intent_response.intent.filters else []
        )
        _safe_log_event(log_service, QueryLogEvent(
            request_id=req_id,
            user_id=principal.user_id,
            role=principal.roles[0] if principal.roles else None,
            scope_type=principal.scoped_roles[0].scope_type.value if principal.scoped_roles else None,
            scope_id=principal.scoped_roles[0].scope_id if principal.scoped_roles else None,
            metric_id=intent_response.intent.metric_id,
            query_type=intent_response.intent.intent_type.value if intent_response.intent.intent_type else None,
            dimensions=list(intent_response.intent.dimensions or []),
            filter_keys=_filter_keys,
            event_type=QueryLogEventType.DRY_RUN,
            status=QueryLogStatus.SUCCESS,
            execution_time_ms=round((time.monotonic() - _query_start_time) * 1000, 2),
            is_follow_up=is_follow_up,
        ))
        return AgentQueryResponse(
            intent=intent_response.intent.model_dump(),
            sql_artifact=validated_artifact.model_dump(),
            result=None,
            execution_metadata=None,
            dry_run=True,
            message="SQL compiled and validated safely (dry run mode).",
            request_id=req_id,
            metric_display_name=meta[0],
            conversation_id=active_conv_id,
            is_follow_up=is_follow_up,
            scope=scope_info,
        )

    # Step 5: Read-only Database Execution and Result Validation
    # DatabaseNotConfiguredError will automatically produce HTTP 503 if not configured
    query_result = execution_service.execute_artifact(
        artifact=validated_artifact,
        principal=principal,
    )

    # Step 6: Deterministic Visualization Selection & Explanation Synthesis
    intent_dict = intent_response.intent.model_dump()
    metric_id = intent_response.intent.metric_id

    is_student_user = principal.has_role("STUDENT") and not principal.has_any_role(
        "PRINCIPAL", "HOD", "DEAN", "IQAC"
    )

    if is_student_list:
        viz = None
        explanation = None
        anomaly_assessment = None
        meta = (
            (f"HOD / {hod_dept_code} Department Student Records", "Department student-level record retrieval")
            if is_hod_user
            else ("Authorized Student Records", "Student-level record retrieval")
        )
    else:
        viz = visualization_service.select_visualization(
            query_result=query_result,
            intent=intent_dict,
            metric_id=metric_id,
        )
        explanation = visualization_service.generate_explanation(
            query_result=query_result,
            intent=intent_dict,
            metric_id=metric_id,
        )
        meta = visualization_service._get_metric_meta(metric_id)
        dept_filters = (intent_response.intent.filters or {}).get("department")
        if intent_response.intent.intent_type == IntentType.COMPARISON_QUERY or (
            isinstance(dept_filters, list) and len(dept_filters) >= 2
        ):
            comp_label = " vs ".join(str(d) for d in dept_filters) if isinstance(dept_filters, list) else ""
            if comp_label:
                meta = (f"{meta[0]} ({comp_label})", meta[1], meta[2])

        if is_hod_user and viz:
            viz.description = f"Scope: HOD / {hod_dept_code} Department"

        if is_student_user and metric_id in ("attendance.percentage", "attendance.raw_percentage"):
            if intent_response.intent.intent_type == IntentType.BREAKDOWN_QUERY:
                meta = ("Student SELF / Subject-wise Attendance", "%", "attendance percentage by course")
                if viz:
                    viz.title = "Student SELF / Subject-wise Attendance"
                    viz.description = "Subject-wise course attendance breakdown for authenticated student."
                    viz.unit = "%"
            else:
                meta = ("Student SELF / Attendance Percentage", "%", "personal attendance percentage")
                if viz:
                    viz.title = "Student SELF / Attendance Percentage"
                    viz.description = "Student self attendance percentage."
                    viz.unit = "%"

        # Step 7: Deterministic Anomaly Detection (Phase 11)
        anomaly_assessment = None
        if settings.ANOMALY_DETECTION_ENABLED and not is_student_user:
            anomaly_assessment = anomaly_service.assess_result(
                query_result=query_result,
                intent=intent_dict,
                metric_id=metric_id,
            )

    # Step 8: Update Conversation Context upon Successful Execution
    if query_result.status == QueryResultStatus.SUCCESS:
        new_turn = (context.turn_count + 1) if context else 1
        if new_turn <= settings.CONVERSATION_MAX_TURNS:
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=settings.CONVERSATION_CONTEXT_TTL_SECONDS
            )
            updated_ctx = ConversationContext(
                conversation_id=active_conv_id,
                user_id=principal.user_id,
                last_metric_id=intent_response.intent.metric_id,
                last_intent_type=intent_response.intent.intent_type,
                last_dimensions=intent_response.intent.dimensions,
                last_filters=intent_response.intent.filters,
                last_time_context=intent_response.intent.time_context,
                last_metric_display_name=meta[0],
                turn_count=new_turn,
                created_at=context.created_at if context else datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                expires_at=expires_at,
            )
            conversation_store.save_context(updated_ctx)
        else:
            logger.info(
                f"Max turns ({settings.CONVERSATION_MAX_TURNS}) reached for conv_id='{active_conv_id}'. Context reset."
            )
            conversation_store.clear_context(active_conv_id, principal)

    # Phase 13: Log successful (or empty) query event
    _log_status = (
        QueryLogStatus.SUCCESS
        if query_result.status == QueryResultStatus.SUCCESS
        else (
            QueryLogStatus.EMPTY
            if query_result.status == QueryResultStatus.EMPTY
            else QueryLogStatus.FAILED
        )
    )
    _filter_keys = (
        list(intent_response.intent.student_filters.keys())
        if is_student_list and intent_response.intent.student_filters
        else list(intent_response.intent.filters.keys()) if intent_response.intent.filters else []
    )
    _safe_log_event(log_service, QueryLogEvent(
        request_id=req_id,
        user_id=principal.user_id,
        role=principal.roles[0] if principal.roles else None,
        scope_type=principal.scoped_roles[0].scope_type.value if principal.scoped_roles else None,
        scope_id=principal.scoped_roles[0].scope_id if principal.scoped_roles else None,
        metric_id=metric_id,
        query_type=intent_response.intent.intent_type.value if intent_response.intent.intent_type else None,
        dimensions=list(intent_response.intent.dimensions or []),
        filter_keys=_filter_keys,
        event_type=QueryLogEventType.FOLLOW_UP_QUERY if is_follow_up else QueryLogEventType.MANUAL_QUERY,
        status=_log_status,
        execution_time_ms=query_result.metadata.execution_time_ms if query_result.metadata else 0.0,
        row_count=query_result.row_count,
        visualization_type=viz.chart_type.value if viz and hasattr(viz, "chart_type") else None,
        anomaly_status=(
            anomaly_assessment.status.value
            if anomaly_assessment and hasattr(anomaly_assessment, "status") else None
        ),
        anomaly_method=(
            anomaly_assessment.method.value
            if anomaly_assessment and hasattr(anomaly_assessment, "method") else None
        ),
        is_follow_up=is_follow_up,
    ))

    # Cache analytical artifact for authorized export and verification
    if not is_student_list and query_result.status in (QueryResultStatus.SUCCESS, QueryResultStatus.EMPTY):
        try:
            artifact_store = get_export_artifact_store()
            artifact_store.save_artifact(
                ExportArtifact(
                    request_id=req_id,
                    user_id=principal.user_id,
                    role=principal.roles[0] if principal.roles else "USER",
                    metric_id=metric_id,
                    metric_display_name=meta[0],
                    query_type=intent_response.intent.intent_type.value if intent_response.intent.intent_type else None,
                    dimensions=list(intent_response.intent.dimensions or []),
                    filters=dict(intent_response.intent.filters or {}),
                    scope_type=principal.scoped_roles[0].scope_type.value if principal.scoped_roles else None,
                    scope_id=principal.scoped_roles[0].scope_id if principal.scoped_roles else None,
                    query_result=query_result,
                    visualization_type=viz.chart_type.value if viz and hasattr(viz, "chart_type") else None,
                    anomaly_status=(
                        anomaly_assessment.status.value
                        if anomaly_assessment and hasattr(anomaly_assessment, "status") else None
                    ),
                )
            )
        except Exception as e:
            logger.warning(f"Failed to cache export artifact (non-fatal): {e}")

    return AgentQueryResponse(
        intent=intent_dict,
        sql_artifact=validated_artifact.model_dump(),
        result=query_result,
        execution_metadata=query_result.metadata,
        dry_run=False,
        message="Query executed and validated successfully.",
        request_id=req_id,
        visualization=viz,
        explanation=explanation,
        metric_display_name=meta[0],
        conversation_id=active_conv_id,
        is_follow_up=is_follow_up,
        anomaly=anomaly_assessment,
        scope=scope_info,
    )
