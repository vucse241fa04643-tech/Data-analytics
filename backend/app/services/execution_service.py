"""Agent 63 - Phase 8: Execution Service
Safely executes validated SQL artifacts against the read-only institutional database,
coordinating pre-execution defense-in-depth, execution limits, and result validation.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from backend.app.core.config import settings
from backend.app.core.errors import (
    DatabaseNotConfiguredError,
    SecurityValidationError,
    SQLValidationError,
)
from backend.app.core.logging import get_logger
from backend.app.schemas.principal import AuthenticatedPrincipal
from backend.app.schemas.query_result import QueryResult, QueryResultStatus
from backend.app.schemas.sql_artifact import SQLArtifact
from backend.app.services.audit import AuditAction, AuthAuditEvent, get_audit_service
from backend.app.services.database import college_database_service
from backend.app.services.result_validator import result_validator
from backend.app.services.sql_validator import get_sql_validator

logger = get_logger("agent63.services.execution_service")

# Regex to find parameter tokens :param_name while avoiding Postgres ::typecast
PARAM_REGEX = re.compile(r"(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)(?!:)")


class ExecutionService:
    """
    Coordinates safe, parameterized, read-only SQL execution and result normalization.
    Enforces strict pre-execution defense-in-depth before touching the database layer.
    """

    def __init__(self):
        self._db_service = college_database_service
        self._validator = result_validator
        self._sql_validator = get_sql_validator()
        self._audit = get_audit_service()

    def validate_artifact_pre_execution(self, artifact: SQLArtifact) -> None:
        """
        Defense-in-depth pre-execution integrity checks:
        1. Confirms validation_status == 'VALID'.
        2. Confirms read_only == True.
        3. Re-runs AST validation (single SELECT, no prohibited constructs).
        4. Verifies all SQL parameter placeholders exist in artifact.parameters.
        """
        if artifact.validation_status != "VALID":
            raise SecurityValidationError(
                f"Cannot execute SQL artifact with status '{artifact.validation_status}'."
            )

        if not artifact.read_only:
            raise SecurityValidationError(
                "Execution rejected: SQL artifact is not flagged as strictly read-only."
            )

        if not artifact.sql or not artifact.sql.strip():
            raise SecurityValidationError("Execution rejected: SQL statement is empty.")

        # Re-verify SQL statement through AST validator
        self._sql_validator.validate_artifact(artifact)

        # Check parameter consistency
        sql_params: Set[str] = set(PARAM_REGEX.findall(artifact.sql))
        provided_params: Set[str] = set(artifact.parameters.keys())
        missing_params = sql_params - provided_params

        if missing_params:
            raise SQLValidationError(
                f"SQL contains unbound parameter placeholders: {', '.join(sorted(missing_params))}."
            )

    def execute_artifact(
        self,
        artifact: SQLArtifact,
        principal: Optional[UserPrincipal] = None,
    ) -> QueryResult:
        """
        Executes a pre-validated SQLArtifact against the institutional database.
        Applies timeouts, row limits, byte limits, and result validation.

        Raises:
            DatabaseNotConfiguredError: If college database is not configured.
            SecurityValidationError: If pre-execution checks fail.
            DatabaseTimeoutError: If execution exceeds statement timeout.
            DatabaseExecutionError: If database driver returns an error.
            ResultValidationError: If output violates semantic sanity checks.
            ResultSizeLimitExceededError: If results breach row or byte limits.
        """
        # Step 1: Pre-execution defense-in-depth checks
        self.validate_artifact_pre_execution(artifact)

        # Step 2: Check database configuration status
        if not settings.is_database_configured:
            logger.info("Execution aborted: institutional database is not configured.")
            raise DatabaseNotConfiguredError("Institutional database connection is not configured.")

        user_role = principal.roles[0] if (principal and principal.roles) else "SYSTEM"
        username = principal.username if principal else "system"

        try:
            # Step 3: Read-only execution
            columns, raw_rows, data_types, exec_time_ms = self._db_service.execute_query(
                sql=artifact.sql,
                parameters=artifact.parameters,
                limit=artifact.limit,
                statement_timeout_ms=settings.COLLEGE_DB_STATEMENT_TIMEOUT,
            )

            # Step 4: Result validation and normalization
            query_result = self._validator.validate_and_normalize(
                raw_columns=columns,
                raw_rows=raw_rows,
                raw_data_types=data_types,
                metric_id=artifact.metric_id,
                execution_time_ms=exec_time_ms,
                statement_timeout_ms=settings.COLLEGE_DB_STATEMENT_TIMEOUT,
                expected_columns=artifact.columns,
            )

            # Step 5: Audit logging
            self._audit.log_event(
                AuthAuditEvent(
                    action=AuditAction.QUERY_EXECUTED,
                    actor_username=username,
                    actor_role=user_role,
                    resource=artifact.metric_id,
                    reason=f"Executed {artifact.query_type} returning {query_result.row_count} rows in {exec_time_ms}ms",
                )
            )

            return query_result

        except Exception as exc:
            # Audit failed query attempts
            self._audit.log_event(
                AuthAuditEvent(
                    action=AuditAction.QUERY_FAILED,
                    actor_username=username,
                    actor_role=user_role,
                    resource=artifact.metric_id,
                    reason=f"Query failed: {type(exc).__name__} - {str(exc).splitlines()[0]}",
                )
            )
            raise


# Singleton instance
execution_service = ExecutionService()
