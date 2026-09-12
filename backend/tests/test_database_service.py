"""
Agent 63 - Phase 8: College Database Service Unit Tests
Tests configuration inspection, parameter translation, timeout application,
read-only enforcement, error mapping, and fail-closed safety.
"""

import asyncio
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from backend.app.core.config import settings
from backend.app.core.errors import (
    DatabaseConnectionError,
    DatabaseExecutionError,
    DatabaseNotConfiguredError,
    DatabaseTimeoutError,
    ResultSizeLimitExceededError,
)
from backend.app.services.database import (
    CollegeDatabaseService,
    DatabaseStatus,
    college_database_service,
    translate_named_parameters,
)
import psycopg
import psycopg.errors


class TestDatabaseServiceUnconfigured:
    """Tests behavior when institutional database is unconfigured (default safe state)."""

    def test_status_reports_not_configured(self):
        with patch.object(settings.__class__, "is_database_configured", False):
            service = CollegeDatabaseService()
            assert service.get_status() == DatabaseStatus.NOT_CONFIGURED
            assert "not configured" in service.get_status_message()

    def test_metadata_does_not_expose_secrets(self):
        with patch.object(settings.__class__, "is_database_configured", True), \
             patch.object(settings, "COLLEGE_DB_HOST", "db.example.edu"), \
             patch.object(settings, "COLLEGE_DB_PASSWORD", "SuperSecretPass123"):
            service = CollegeDatabaseService()
            metadata = service.get_safe_metadata()
            assert "password" not in metadata
            assert "SuperSecretPass123" not in str(metadata)

    def test_check_connection_unconfigured(self):
        with patch.object(settings.__class__, "is_database_configured", False):
            service = CollegeDatabaseService()
            result = asyncio.run(service.check_connection())
            assert result["status"] == DatabaseStatus.NOT_CONFIGURED
            assert result["connected"] is False

    def test_execute_query_fails_closed_when_unconfigured(self):
        with patch.object(settings.__class__, "is_database_configured", False):
            service = CollegeDatabaseService()
            with pytest.raises(DatabaseNotConfiguredError) as exc_info:
                service.execute_query(sql="SELECT 1;")
            assert "not configured" in str(exc_info.value)


class TestNamedParameterTranslation:
    """Tests translation of :param placeholders to driver-native %(param)s format."""

    def test_basic_parameter_translation(self):
        sql = "SELECT * FROM students WHERE dept = :dept_id AND batch = :batch_id;"
        translated = translate_named_parameters(sql)
        assert translated == "SELECT * FROM students WHERE dept = %(dept_id)s AND batch = %(batch_id)s;"

    def test_preserves_postgres_type_casts(self):
        sql = "SELECT id::text, val::integer FROM marks WHERE student_id = :student_id AND score > :min_score::numeric;"
        translated = translate_named_parameters(sql)
        assert "%(student_id)s" in translated
        assert "%(min_score)s::numeric" in translated
        assert "::text" in translated
        assert "::integer" in translated
        assert "%(text)s" not in translated
        assert "%(integer)s" not in translated


class TestDatabaseExecutionMocked:
    """Tests execution pipeline, limits, and error mappings with mocked psycopg."""

    @patch("backend.app.services.database.psycopg.connect")
    def test_successful_query_execution(self, mock_connect):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        # Mock cursor description and return data
        col1 = MagicMock()
        col1.name = "metric_value"
        col1.type_display = "numeric"
        col2 = MagicMock()
        col2.name = "term"
        col2.type_display = "text"
        mock_cur.description = [col1, col2]
        mock_cur.fetchmany.return_value = [
            {"metric_value": Decimal("88.50"), "term": "SEM_1"}
        ]

        with patch.object(settings.__class__, "is_database_configured", True), \
             patch.object(settings, "COLLEGE_DB_HOST", "postgres.college.edu"), \
             patch.object(settings, "COLLEGE_DB_PASSWORD", "pwd123"), \
             patch.object(settings, "COLLEGE_DB_NAME", "collegedb"), \
             patch.object(settings, "COLLEGE_DB_USER", "agent63_user"):
            service = CollegeDatabaseService()
            cols, rows, data_types, elapsed = service.execute_query(
                sql="SELECT metric_value, term FROM analytics WHERE term = :t LIMIT 100;",
                parameters={"t": "SEM_1"},
                limit=50,
            )

            assert cols == ["metric_value", "term"]
            assert len(rows) == 1
            assert rows[0]["metric_value"] == Decimal("88.50")
            assert data_types["metric_value"] == "numeric"
            assert elapsed >= 0
            assert mock_conn.read_only is True

            # Verify session characteristics and statement timeout were set
            calls = [c[0][0] for c in mock_cur.execute.call_args_list]
            assert any("TRANSACTION READ ONLY" in c for c in calls)
            assert any("statement_timeout" in c for c in calls)

    @patch("backend.app.services.database.psycopg.connect")
    def test_row_limit_breach_raises_exception(self, mock_connect):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        col = MagicMock()
        col.name = "id"
        mock_cur.description = [col]
        # Return 6 rows when limit is 5
        mock_cur.fetchmany.return_value = [{"id": i} for i in range(6)]

        with patch.object(settings.__class__, "is_database_configured", True), \
             patch.object(settings, "COLLEGE_DB_HOST", "postgres.college.edu"), \
             patch.object(settings, "COLLEGE_DB_PASSWORD", "pwd123"), \
             patch.object(settings, "COLLEGE_DB_NAME", "collegedb"), \
             patch.object(settings, "COLLEGE_DB_USER", "agent63_user"):
            service = CollegeDatabaseService()
            with pytest.raises(ResultSizeLimitExceededError):
                service.execute_query(sql="SELECT id FROM t LIMIT 5;", limit=5)

    @patch("backend.app.services.database.psycopg.connect")
    def test_statement_timeout_maps_to_database_timeout_error(self, mock_connect):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        mock_cur.execute.side_effect = psycopg.errors.QueryCanceled("canceling statement due to statement timeout")

        with patch.object(settings.__class__, "is_database_configured", True), \
             patch.object(settings, "COLLEGE_DB_HOST", "postgres.college.edu"), \
             patch.object(settings, "COLLEGE_DB_PASSWORD", "pwd123"), \
             patch.object(settings, "COLLEGE_DB_NAME", "collegedb"), \
             patch.object(settings, "COLLEGE_DB_USER", "agent63_user"):
            service = CollegeDatabaseService()
            with pytest.raises(DatabaseTimeoutError):
                service.execute_query(sql="SELECT 1;")

    @patch("backend.app.services.database.psycopg.connect")
    def test_read_only_violation_maps_to_database_execution_error(self, mock_connect):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        mock_cur.execute.side_effect = psycopg.errors.ReadOnlySqlTransaction("cannot execute INSERT in a read-only transaction")

        with patch.object(settings.__class__, "is_database_configured", True), \
             patch.object(settings, "COLLEGE_DB_HOST", "postgres.college.edu"), \
             patch.object(settings, "COLLEGE_DB_PASSWORD", "pwd123"), \
             patch.object(settings, "COLLEGE_DB_NAME", "collegedb"), \
             patch.object(settings, "COLLEGE_DB_USER", "agent63_user"):
            service = CollegeDatabaseService()
            with pytest.raises(DatabaseExecutionError) as exc_info:
                service.execute_query(sql="INSERT INTO t VALUES (1);")
            assert "write operations are strictly prohibited" in str(exc_info.value)

    @patch("backend.app.services.database.psycopg.connect")
    def test_operational_error_maps_to_connection_error(self, mock_connect):
        mock_connect.side_effect = psycopg.OperationalError("could not translate host name")

        with patch.object(settings.__class__, "is_database_configured", True), \
             patch.object(settings, "COLLEGE_DB_HOST", "bad.host.edu"), \
             patch.object(settings, "COLLEGE_DB_PASSWORD", "pwd123"), \
             patch.object(settings, "COLLEGE_DB_NAME", "collegedb"), \
             patch.object(settings, "COLLEGE_DB_USER", "agent63_user"):
            service = CollegeDatabaseService()
            with pytest.raises(DatabaseConnectionError):
                service.execute_query(sql="SELECT 1;")
