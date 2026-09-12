"""Agent 63 - Phase 8: Agent Query API Endpoint
Accepts natural language analytical questions, orchestrates intent interpretation,
deterministic SQL compilation, AST safety validation, and safe read-only database execution.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, status

from backend.app.core.config import settings
from backend.app.core.errors import AuthorizationError, DatabaseNotConfiguredError
from backend.app.core.logging import get_logger, request_id_ctx_var
from backend.app.dependencies.auth import get_current_principal
from backend.app.schemas.conversation_context import ConversationContext
from backend.app.schemas.intent import IntentRequest, IntentValidationStatus
from backend.app.schemas.principal import AuthenticatedPrincipal
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
from backend.app.services.sql_compiler import SQLCompiler, get_sql_compiler
from backend.app.services.sql_validator import SQLValidator, get_sql_validator

from backend.app.services.visualization_service import (
    VisualizationService,
    get_visualization_service,
)

logger = get_logger("agent63.api.agent")

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
    conversation_store: ConversationContextStore = Depends(get_conversation_store),
) -> AgentQueryResponse:
    """Orchestrates end-to-end natural language query execution with defense-in-depth."""
    req_id = request_id_ctx_var.get()

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
        err = AuthorizationError(message=msg)
        err.code = err_code
        raise err

    if intent_response.status != IntentValidationStatus.VALID or not intent_response.intent:
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

    # Step 4: Check if dry-run requested
    if payload.dry_run:
        logger.info("Dry-run requested: skipping database execution.")
        meta = visualization_service._get_metric_meta(intent_response.intent.metric_id)

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

    # Step 7: Update Conversation Context upon Successful Execution
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
    )
