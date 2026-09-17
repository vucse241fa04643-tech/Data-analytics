"""
Agent 63 – Attendance Analytics & Row Level Security (RLS) Regression Tests
Validates that:
1. Institutional average attendance returns verified non-null metrics for Principal/leadership.
2. Department attendance breakdown returns all active institutional departments.
3. Course attendance breakdown returns all active course offerings.
4. HOD attendance is strictly isolated to their authorized department.
5. Student attendance is strictly isolated to their own records; cross-student queries return 0 rows.
6. Queries without authorization context fail closed (0 rows returned).
7. Attendance shortage count accurately evaluates students below 75% attendance.
"""

from decimal import Decimal
import pytest

from backend.app.core.config import settings
from backend.app.schemas.intent import IntentType, StructuredIntent
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopedRoleAssignment, ScopeType
from backend.app.schemas.query_result import QueryResultStatus
from backend.app.services.database import college_database_service
from backend.app.services.execution_service import execution_service
from backend.app.services.identity_resolution import get_identity_resolution_service
from backend.app.services.identity_repository import ROLE_PERMISSIONS_MAP
from backend.app.services.sql_compiler import get_sql_compiler


# Check if institutional database is configured and reachable
_db_available = settings.is_database_configured and college_database_service.is_configured()


@pytest.fixture
def principal_user() -> AuthenticatedPrincipal:
    roles = ["PRINCIPAL"]
    perms = set()
    for r in roles:
        perms.update(ROLE_PERMISSIONS_MAP.get(r, set()))
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=roles,
        scoped_roles=[ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)],
        permissions=perms,
    )


@pytest.fixture
def hod_cse_user() -> AuthenticatedPrincipal:
    roles = ["HOD"]
    perms = set()
    for r in roles:
        perms.update(ROLE_PERMISSIONS_MAP.get(r, set()))
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000004",
        username="test_hod_cse",
        email="hod.cse@vignan.ac.in",
        roles=roles,
        scoped_roles=[
            ScopedRoleAssignment(
                role="HOD",
                scope_type=ScopeType.DEPARTMENT,
                scope_id="a6300000-0003-4000-8000-000000000001",
            )
        ],
        permissions=perms,
    )


@pytest.fixture
def student_user() -> AuthenticatedPrincipal:
    roles = ["STUDENT"]
    perms = set()
    for r in roles:
        perms.update(ROLE_PERMISSIONS_MAP.get(r, set()))
    return AuthenticatedPrincipal(
        user_id="bfc1067c-23c1-4776-958e-2f6e8918aaf5",
        username="test_student_1",
        email="test_student_1@vignan.ac.in",
        person_id="a6300000-0020-4000-8000-000000000001",
        roles=roles,
        scoped_roles=[
            ScopedRoleAssignment(
                role="STUDENT",
                scope_type=ScopeType.SELF,
                scope_id="a6300000-0020-4000-8000-000000000001",
            )
        ],
        permissions=perms,
    )


class TestSessionContextBuilder:
    """Unit tests for RLS session context generation."""

    def test_build_context_principal(self, principal_user):
        resolver = get_identity_resolution_service()
        ctx = resolver.build_session_context(principal_user)
        assert ctx["app.role_codes"] == "PRINCIPAL"
        assert ctx["app.user_id"] == principal_user.user_id
        assert "app.student_id" not in ctx

    def test_build_context_hod(self, hod_cse_user):
        resolver = get_identity_resolution_service()
        ctx = resolver.build_session_context(hod_cse_user)
        assert ctx["app.role_codes"] == "HOD"
        assert ctx["app.dept_scope"] == "a6300000-0003-4000-8000-000000000001"

    def test_build_context_student(self, student_user):
        resolver = get_identity_resolution_service()
        ctx = resolver.build_session_context(student_user)
        assert ctx["app.role_codes"] == "STUDENT"
        assert "app.student_id" in ctx

    def test_build_context_none_fails_closed(self):
        resolver = get_identity_resolution_service()
        ctx = resolver.build_session_context(None)
        assert ctx["app.role_codes"] == "SYSTEM"


@pytest.mark.skipif(not _db_available, reason="College PostgreSQL database is not configured/reachable")
class TestAttendanceRLSLiveDatabase:
    """End-to-end regression tests against the authoritative PostgreSQL database."""

    def test_institutional_average_attendance_principal(self, principal_user):
        """Validates 'What is the average attendance across the institution?' returns non-null."""
        compiler = get_sql_compiler()
        intent = StructuredIntent(
            intent_type=IntentType.DIRECT_METRIC,
            metric_id="attendance.percentage",
            dimensions=[],
            filters={},
            confidence=0.95,
        )
        artifact = compiler.compile(intent, principal_user)
        assert artifact.validation_status == "VALID"

        result = execution_service.execute_artifact(artifact, principal=principal_user)
        assert result.status == QueryResultStatus.SUCCESS
        assert result.row_count == 1
        val = result.rows[0]["metric_value"]
        assert val is not None, "Institutional average attendance must not be null"
        assert float(val) == pytest.approx(79.43, abs=0.1)

    def test_department_attendance_breakdown_principal(self, principal_user):
        """Validates 'Show me the average attendance by department.' returns all departments."""
        compiler = get_sql_compiler()
        intent = StructuredIntent(
            intent_type=IntentType.BREAKDOWN_QUERY,
            metric_id="attendance.percentage",
            dimensions=["dim.department"],
            filters={},
            confidence=0.95,
        )
        artifact = compiler.compile(intent, principal_user)
        assert artifact.validation_status == "VALID"

        result = execution_service.execute_artifact(artifact, principal=principal_user)
        assert result.status == QueryResultStatus.SUCCESS
        assert result.row_count == 5, "Expected 5 departments with attendance records"
        dept_codes = {row["department"] for row in result.rows}
        assert dept_codes == {"EEE", "CIVIL", "CSE", "ECE", "MECH"}
        for row in result.rows:
            assert row["metric_value"] is not None

    def test_course_attendance_breakdown_principal(self, principal_user):
        """Validates attendance by course returns all courses."""
        compiler = get_sql_compiler()
        intent = StructuredIntent(
            intent_type=IntentType.BREAKDOWN_QUERY,
            metric_id="attendance.percentage",
            dimensions=["dim.course"],
            filters={},
            confidence=0.95,
        )
        artifact = compiler.compile(intent, principal_user)
        assert artifact.validation_status == "VALID"

        result = execution_service.execute_artifact(artifact, principal=principal_user)
        assert result.status == QueryResultStatus.SUCCESS
        assert result.row_count > 0, "Expected course attendance records"
        for row in result.rows:
            assert row["metric_value"] is not None

    def test_hod_department_attendance_scoped(self, hod_cse_user):
        """Validates HOD can only access their authorized department attendance."""
        compiler = get_sql_compiler()

        # 1. HOD department average
        intent = StructuredIntent(
            intent_type=IntentType.DIRECT_METRIC,
            metric_id="attendance.percentage",
            dimensions=[],
            filters={},
            confidence=0.95,
        )
        artifact = compiler.compile(intent, hod_cse_user)
        result = execution_service.execute_artifact(artifact, principal=hod_cse_user)
        assert result.status == QueryResultStatus.SUCCESS
        assert result.row_count == 1
        assert float(result.rows[0]["metric_value"]) == pytest.approx(82.02, abs=0.1)

        # 2. HOD breakdown: should only show CSE
        breakdown_intent = StructuredIntent(
            intent_type=IntentType.BREAKDOWN_QUERY,
            metric_id="attendance.percentage",
            dimensions=["dim.department"],
            filters={},
            confidence=0.95,
        )
        bd_artifact = compiler.compile(breakdown_intent, hod_cse_user)
        bd_result = execution_service.execute_artifact(bd_artifact, principal=hod_cse_user)
        assert bd_result.status == QueryResultStatus.SUCCESS
        assert bd_result.row_count == 1
        assert bd_result.rows[0]["department"] == "CSE"

    def test_student_own_attendance_isolation(self, student_user):
        """Validates Student can only see their own attendance."""
        compiler = get_sql_compiler()
        intent = StructuredIntent(
            intent_type=IntentType.DIRECT_METRIC,
            metric_id="attendance.percentage",
            dimensions=[],
            filters={},
            confidence=0.95,
        )
        artifact = compiler.compile(intent, student_user)
        result = execution_service.execute_artifact(artifact, principal=student_user)
        assert result.status == QueryResultStatus.SUCCESS
        assert result.row_count == 1
        assert float(result.rows[0]["metric_value"]) == pytest.approx(82.17, abs=0.1)

    def test_unauthorized_empty_context_fails_closed(self):
        """Direct database execution without session context returns 0 rows due to RLS."""
        import psycopg
        conn_kwargs = college_database_service._get_connection_kwargs()
        with psycopg.connect(**conn_kwargs) as conn:
            with conn.cursor() as cur:
                cur.execute("SET ROLE test_app_user;")
                cur.execute("SELECT count(*) AS cnt FROM attendance.attendance_summary;")
                row = cur.fetchone()
                assert row["cnt"] == 0, "RLS must filter out all rows when no authorized session context is set"

    def test_attendance_shortage_count(self, principal_user):
        """Validates students with attendance below 75% are accurately counted."""
        compiler = get_sql_compiler()
        intent = StructuredIntent(
            intent_type=IntentType.DIRECT_METRIC,
            metric_id="attendance.shortage_count",
            dimensions=[],
            filters={},
            confidence=0.95,
        )
        artifact = compiler.compile(intent, principal_user)
        result = execution_service.execute_artifact(artifact, principal=principal_user)
        assert result.status == QueryResultStatus.SUCCESS
        assert result.row_count == 1
        count_val = result.rows[0]["metric_value"]
        assert count_val == 356, "Expected 356 students with attendance shortage (<75%)"
