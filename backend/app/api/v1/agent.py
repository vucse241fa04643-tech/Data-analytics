"""Agent 63 - Phase 8: Agent Query API Endpoint
Accepts natural language analytical questions, orchestrates intent interpretation,
deterministic SQL compilation, AST safety validation, and safe read-only database execution.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from backend.app.core.errors import DatabaseNotConfiguredError
from backend.app.core.logging import get_logger, request_id_ctx_var
from backend.app.dependencies.auth import get_current_principal
from backend.app.schemas.intent import IntentRequest, IntentValidationStatus
from backend.app.schemas.principal import AuthenticatedPrincipal
from backend.app.schemas.query_result import (
    AgentQueryRequest,
    AgentQueryResponse,
    QueryResult,
    QueryResultStatus,
)
from backend.app.services.execution_service import execution_service
from backend.app.services.intent_service import IntentService, get_intent_service
from backend.app.services.sql_compiler import SQLCompiler, get_sql_compiler
from backend.app.services.sql_validator import SQLValidator, get_sql_validator

logger = get_logger("agent63.api.agent")

router = APIRouter(prefix="/agent", tags=["Agent Query Execution"])


@router.post(
    "/query",
    response_model=AgentQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="End-to-end analytical query execution",
    description=(
        "Translates natural language to authorized StructuredIntent, compiles deterministic SQL, "
        "validates AST safety, and executes safely against the read-only institutional database."
    ),
)
def execute_agent_query(
    payload: AgentQueryRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    intent_service: IntentService = Depends(get_intent_service),
    sql_compiler: SQLCompiler = Depends(get_sql_compiler),
    sql_validator: SQLValidator = Depends(get_sql_validator),
) -> AgentQueryResponse:
    """Orchestrates end-to-end natural language query execution with defense-in-depth."""
    req_id = request_id_ctx_var.get()

    # Step 1: Natural Language -> StructuredIntent
    intent_req = IntentRequest(message=payload.prompt)
    intent_response = intent_service.interpret_intent(
        request=intent_req,
        principal=principal,
        request_id=req_id,
    )

    if intent_response.status != IntentValidationStatus.VALID or not intent_response.intent:
        return AgentQueryResponse(
            intent=intent_response.intent.model_dump() if intent_response.intent else None,
            sql_artifact=None,
            result=None,
            execution_metadata=None,
            dry_run=payload.dry_run,
            message=intent_response.message or "Query intent could not be validated for analytical execution.",
            request_id=req_id,
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
        return AgentQueryResponse(
            intent=intent_response.intent.model_dump(),
            sql_artifact=validated_artifact.model_dump(),
            result=None,
            execution_metadata=None,
            dry_run=True,
            message="SQL compiled and validated safely (dry run mode).",
            request_id=req_id,
        )

    # Step 5: Read-only Database Execution and Result Validation
    # DatabaseNotConfiguredError will automatically produce HTTP 503 if not configured
    query_result = execution_service.execute_artifact(
        artifact=validated_artifact,
        principal=principal,
    )

    return AgentQueryResponse(
        intent=intent_response.intent.model_dump(),
        sql_artifact=validated_artifact.model_dump(),
        result=query_result,
        execution_metadata=query_result.metadata,
        dry_run=False,
        message="Query executed and validated successfully.",
        request_id=req_id,
    )
