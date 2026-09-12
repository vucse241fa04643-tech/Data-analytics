"""
Agent 63 - Phase 8: Execution Service Unit Tests
Tests defense-in-depth pre-execution validation, fail-closed handling when database
is unconfigured, audit event dispatch, and read-only execution orchestration.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from backend.app.core.config import settings
from backend.app.core.errors import (
    DatabaseExecutionError,
    DatabaseNotConfiguredError,
    SecurityValidationError,
    SQLValidationError,
)
from backend.app.schemas.principal import AuthenticatedPrincipal
from backend.app.schemas.query_result import QueryResultStatus
from backend.app.schemas.sql_artifact import SQLArtifact
from backend.app.services.audit import AuditAction
from backend.app.services.execution_service import ExecutionService, execution_service


@pytest.fixture
def mock_principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id="usr-12345",
        username="faculty_user",
        email="faculty@college.edu",
        roles=["FACULTY"],
        scoped_roles=[],
        permissions={"analytics:query"},
    )


@pytest.fixture
def valid_sql_artifact() -> SQLArtifact:
    return SQLArtifact(
        sql="""
        SELECT a.adjusted_pct, a.student_id
        FROM attendance.v_current_attendance a
        WHERE a.term_id = :term_id
        LIMIT 100;
        """,
        parameters={"term_id": "TERM-2026-ODD"},
        metric_id="attendance.percentage",
        tables=["attendance.v_current_attendance"],
        columns=["adjusted_pct", "student_id"],
        joins=[],
        filters=["term_id"],
        authorization_predicates=[],
        query_type="METRIC_QUERY",
        limit=100,
        read_only=True,
        validation_status="VALID",
    )


class TestExecutionServicePreValidation:
    """Tests defense-in-depth pre-execution integrity checks."""

    def test_rejects_non_valid_status(self, valid_sql_artifact):
        valid_sql_artifact.validation_status = "PENDING_VALIDATION"
        with pytest.raises(SecurityValidationError) as exc_info:
            execution_service.validate_artifact_pre_execution(valid_sql_artifact)
        assert "Cannot execute SQL artifact with status" in str(exc_info.value)

    def test_rejects_non_read_only_artifact(self, valid_sql_artifact):
        valid_sql_artifact.read_only = False
        with pytest.raises(SecurityValidationError) as exc_info:
            execution_service.validate_artifact_pre_execution(valid_sql_artifact)
        assert "not flagged as strictly read-only" in str(exc_info.value)

    def test_rejects_empty_sql_artifact(self, valid_sql_artifact):
        valid_sql_artifact.sql = "   "
        with pytest.raises(SecurityValidationError) as exc_info:
            execution_service.validate_artifact_pre_execution(valid_sql_artifact)
        assert "SQL statement is empty" in str(exc_info.value)

    def test_rejects_unbound_parameter_placeholder(self, valid_sql_artifact):
        valid_sql_artifact.sql = """
        SELECT a.adjusted_pct
        FROM attendance.v_current_attendance a
        WHERE a.term_id = :term_id AND a.dept_id = :unbound_dept
        LIMIT 100;
        """
        with pytest.raises(SQLValidationError) as exc_info:
            execution_service.validate_artifact_pre_execution(valid_sql_artifact)
        assert "unbound parameter placeholders: unbound_dept" in str(exc_info.value)

    def test_passes_valid_artifact(self, valid_sql_artifact):
        # Should complete without error
        execution_service.validate_artifact_pre_execution(valid_sql_artifact)


class TestExecutionServiceOrchestration:
    """Tests execution against database service and audit dispatch."""

    def test_fails_closed_when_database_unconfigured(self, valid_sql_artifact, mock_principal):
        with patch.object(settings.__class__, "is_database_configured", False):
            with pytest.raises(DatabaseNotConfiguredError):
                execution_service.execute_artifact(valid_sql_artifact, principal=mock_principal)

    @patch("backend.app.services.execution_service.college_database_service.execute_query")
    @patch("backend.app.services.execution_service.get_audit_service")
    def test_successful_execution_and_audit(
        self, mock_get_audit, mock_db_execute, valid_sql_artifact, mock_principal
    ):
        mock_audit = MagicMock()
        mock_get_audit.return_value = mock_audit

        # Mock database returning raw execution rows
        mock_db_execute.return_value = (
            ["adjusted_pct", "student_id"],
            [{"adjusted_pct": Decimal("85.50"), "student_id": "STU101"}],
            {"adjusted_pct": "numeric", "student_id": "text"},
            14.2,
        )

        with patch.object(settings.__class__, "is_database_configured", True):
            service = ExecutionService()
            service._audit = mock_audit
            result = service.execute_artifact(valid_sql_artifact, principal=mock_principal)

            assert result.status == QueryResultStatus.SUCCESS
            assert result.row_count == 1
            assert result.rows[0]["adjusted_pct"] == 85.50
            assert result.metadata.execution_time_ms == 14.2

            # Verify audit event logged
            mock_audit.log_event.assert_called_once()
            call_event = mock_audit.log_event.call_args[0][0]
            assert call_event.action == AuditAction.QUERY_EXECUTED
            assert call_event.actor_username == "faculty_user"
            assert call_event.actor_role == "FACULTY"

    @patch("backend.app.services.execution_service.college_database_service.execute_query")
    @patch("backend.app.services.execution_service.get_audit_service")
    def test_failed_execution_logs_failure_audit(
        self, mock_get_audit, mock_db_execute, valid_sql_artifact, mock_principal
    ):
        mock_audit = MagicMock()
        mock_get_audit.return_value = mock_audit

        mock_db_execute.side_effect = DatabaseExecutionError("Driver level failure")

        with patch.object(settings.__class__, "is_database_configured", True):
            service = ExecutionService()
            service._audit = mock_audit
            with pytest.raises(DatabaseExecutionError):
                service.execute_artifact(valid_sql_artifact, principal=mock_principal)

            # Verify audit failure event logged
            mock_audit.log_event.assert_called_once()
            call_event = mock_audit.log_event.call_args[0][0]
            assert call_event.action == AuditAction.QUERY_FAILED
            assert call_event.actor_username == "faculty_user"
