"""
Agent 63 – SQL Golden Snapshot Test Suite (Phase 7)
Verifies deterministic, reproducible SQL compilation against canonical snapshot expectations.
Zero database execution. No PostgreSQL connection is made.
"""

import pytest
from backend.app.schemas.intent import (
    IntentType,
    StructuredIntent,
    TimeContext,
)
from backend.app.schemas.principal import (
    AuthenticatedPrincipal,
    ScopeType,
    ScopedRoleAssignment,
)
from backend.app.services.sql_compiler import get_sql_compiler


@pytest.fixture
def compiler():
    return get_sql_compiler()


@pytest.fixture
def campus_principal():
    return AuthenticatedPrincipal(
        user_id="user-principal-golden",
        username="principal",
        email="principal@college.edu",
        roles=["PRINCIPAL"],
        scoped_roles=[
            ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)
        ],
        permissions={"analytics.read", "attendance.read", "assessment.read", "academics.read"},
    )


@pytest.fixture
def hod_ece():
    return AuthenticatedPrincipal(
        user_id="user-hod-ece-golden",
        username="hod_ece",
        email="hod_ece@college.edu",
        roles=["HOD"],
        scoped_roles=[
            ScopedRoleAssignment(role="HOD", scope_type=ScopeType.DEPARTMENT, scope_id="ECE")
        ],
        permissions={"analytics.read", "attendance.read", "assessment.read", "academics.read"},
    )


def test_golden_snapshot_attendance_metric_cse(compiler, campus_principal):
    """Snapshot: Attendance percentage for CSE department."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
        filters={"department": "CSE"},
    )
    artifact = compiler.compile(intent, campus_principal)

    expected_sql = (
        "SELECT round(avg(a.adjusted_pct), 2) AS metric_value\n"
        "FROM attendance.v_current_attendance a\n"
        "JOIN academics.course_offering co ON co.course_offering_id = a.course_offering_id JOIN core.department d ON d.department_id = co.department_id\n"
        "WHERE d.code = :param_0\n"
        "LIMIT 100"
    )

    assert artifact.sql.strip() == expected_sql.strip()
    assert artifact.parameters == {"param_0": "CSE"}
    assert artifact.metric_id == "attendance.percentage"
    assert artifact.limit == 100
    assert artifact.read_only is True


def test_golden_snapshot_pass_percentage_breakdown(compiler, campus_principal):
    """Snapshot: Course pass percentage breakdown by department."""
    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        metric_id="assessment.course_pass_percentage",
        dimensions=["department"],
    )
    artifact = compiler.compile(intent, campus_principal)

    expected_sql = (
        "SELECT d.code AS department, round(avg(cp.pass_pct), 2) AS metric_value\n"
        "FROM assessment.v_course_performance cp\n"
        "JOIN core.department d ON d.department_id = cp.department_id\n"
        "GROUP BY d.code\n"
        "ORDER BY metric_value DESC\n"
        "LIMIT 100"
    )

    assert artifact.sql.strip() == expected_sql.strip()
    assert artifact.parameters == {}
    assert artifact.query_type == "BREAKDOWN_QUERY"


def test_golden_snapshot_active_student_strength(compiler, campus_principal):
    """Snapshot: Active student strength query."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="academics.active_student_strength",
        filters={"status": "ACTIVE"},
    )
    artifact = compiler.compile(intent, campus_principal)

    expected_sql = (
        "SELECT count(DISTINCT s.student_id) FILTER (WHERE s.status = 'ACTIVE') AS metric_value\n"
        "FROM people.student s\n"
        "WHERE s.status = :param_0\n"
        "LIMIT 100"
    )

    assert artifact.sql.strip() == expected_sql.strip()
    assert artifact.parameters == {"param_0": "ACTIVE"}


def test_golden_snapshot_attendance_trend_terms(compiler, campus_principal):
    """Snapshot: Attendance trend over terms."""
    intent = StructuredIntent(
        intent_type=IntentType.TREND_QUERY,
        metric_id="attendance.percentage",
        dimensions=["term"],
    )
    artifact = compiler.compile(intent, campus_principal)

    expected_sql = (
        "SELECT t.label AS term, round(avg(a.adjusted_pct), 2) AS metric_value\n"
        "FROM attendance.v_current_attendance a\n"
        "JOIN core.term t ON t.term_id = a.term_id\n"
        "GROUP BY t.label\n"
        "ORDER BY t.label ASC\n"
        "LIMIT 100"
    )

    assert artifact.sql.strip() == expected_sql.strip()
    assert artifact.parameters == {}
    assert artifact.query_type == "TREND_QUERY"


def test_golden_snapshot_hod_department_scoping(compiler, hod_ece):
    """Snapshot: HOD query automatically scoped to ECE department."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
    )
    artifact = compiler.compile(intent, hod_ece)

    expected_sql = (
        "SELECT round(avg(a.adjusted_pct), 2) AS metric_value\n"
        "FROM attendance.v_current_attendance a\n"
        "JOIN academics.course_offering co ON co.course_offering_id = a.course_offering_id JOIN core.department d ON d.department_id = co.department_id\n"
        "WHERE d.code = :auth_department_code\n"
        "LIMIT 100"
    )

    assert artifact.sql.strip() == expected_sql.strip()
    assert artifact.parameters == {"auth_department_code": "ECE"}
    assert "d.code = :auth_department_code" in artifact.authorization_predicates
