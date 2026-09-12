"""
Agent 63 – SQL Compiler Test Suite (Phase 7)
Tests deterministic compilation of validated StructuredIntent into parameterized SQLArtifacts.
Validates:
1. Canonical metric queries (attendance.percentage, assessment.course_pass_percentage, academics.active_student_strength)
2. All 5 query archetypes (METRIC_QUERY, BREAKDOWN_QUERY, COMPARISON_QUERY, TREND_QUERY, RANKING_QUERY)
3. Strict parameter separation (no user filter values in SQL strings)
4. Server-side authorization predicate injection for STUDENT and HOD roles
5. Rejection of cross-scope requests (e.g. HOD requesting foreign department)
"""

import pytest
from backend.app.core.errors import (
    SQLAuthorizationError,
    SQLCompilationError,
    SQLValidationError,
)
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
from backend.app.schemas.sql_artifact import SQLArtifact
from backend.app.services.sql_compiler import SQLCompiler, get_sql_compiler


@pytest.fixture
def compiler() -> SQLCompiler:
    return get_sql_compiler()


@pytest.fixture
def principal_user() -> AuthenticatedPrincipal:
    """College Principal with campus-wide access."""
    return AuthenticatedPrincipal(
        user_id="user-principal-01",
        username="principal_office",
        email="principal@college.edu",
        roles=["PRINCIPAL"],
        scoped_roles=[
            ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)
        ],
        permissions={"analytics.read", "attendance.read", "assessment.read", "academics.read"},
    )


@pytest.fixture
def hod_cse_user() -> AuthenticatedPrincipal:
    """HOD of Computer Science & Engineering."""
    return AuthenticatedPrincipal(
        user_id="user-hod-cse-01",
        username="hod_cse",
        email="hod_cse@college.edu",
        roles=["HOD"],
        scoped_roles=[
            ScopedRoleAssignment(
                role="HOD",
                scope_type=ScopeType.DEPARTMENT,
                scope_id="CSE",
            )
        ],
        permissions={"analytics.read", "attendance.read", "assessment.read", "academics.read"},
    )


@pytest.fixture
def student_user() -> AuthenticatedPrincipal:
    """Individual enrolled student."""
    return AuthenticatedPrincipal(
        user_id="user-student-01",
        username="john_doe_student",
        email="john@college.edu",
        person_id="person-student-01",
        roles=["STUDENT"],
        scoped_roles=[
            ScopedRoleAssignment(
                role="STUDENT",
                scope_type=ScopeType.SELF,
                scope_id="person-student-01",
            )
        ],
        permissions={"analytics.read", "attendance.read"},
    )


# -------------------------------------------------------------------------
# Canonical Metric Compilation Tests
# -------------------------------------------------------------------------

def test_compile_attendance_percentage_metric_query(compiler, principal_user):
    """Compiles attendance.percentage for principal (unconstrained, parameterized)."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
        filters={"department": "CSE"},
    )
    artifact = compiler.compile(intent=intent, principal=principal_user)

    assert isinstance(artifact, SQLArtifact)
    assert artifact.read_only is True
    assert artifact.validation_status == "VALID"
    assert "attendance.v_current_attendance" in artifact.sql
    assert "round(avg(a.adjusted_pct), 2)" in artifact.sql
    assert "d.code = :param_0" in artifact.sql
    assert artifact.parameters["param_0"] == "CSE"
    assert "CSE" not in artifact.sql  # Strict parameter separation
    assert "LIMIT" in artifact.sql


def test_compile_course_pass_percentage_breakdown(compiler, principal_user):
    """Compiles assessment.course_pass_percentage breakdown by department."""
    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        metric_id="assessment.course_pass_percentage",
        dimensions=["department"],
    )
    artifact = compiler.compile(intent=intent, principal=principal_user)

    assert artifact.read_only is True
    assert "assessment.v_course_performance" in artifact.sql
    assert "round(avg(cp.pass_pct), 2)" in artifact.sql
    assert "d.code AS department" in artifact.sql
    assert "GROUP BY d.code" in artifact.sql
    assert "ORDER BY metric_value DESC" in artifact.sql


def test_compile_active_student_strength_metric_query(compiler, principal_user):
    """Compiles academics.active_student_strength query."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="academics.active_student_strength",
        filters={"status": "ACTIVE"},
    )
    artifact = compiler.compile(intent=intent, principal=principal_user)

    assert "people.student" in artifact.sql
    assert "count(DISTINCT s.student_id) FILTER (WHERE s.status = 'ACTIVE')" in artifact.sql
    assert "s.status = :param_0" in artifact.sql
    assert artifact.parameters["param_0"] == "ACTIVE"


# -------------------------------------------------------------------------
# Archetype Tests
# -------------------------------------------------------------------------

def test_compile_comparison_query_multiple_departments(compiler, principal_user):
    """Compiles COMPARISON_QUERY comparing CSE and ECE."""
    intent = StructuredIntent(
        intent_type=IntentType.COMPARISON_QUERY,
        metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": ["CSE", "ECE"]},
    )
    artifact = compiler.compile(intent=intent, principal=principal_user)

    assert "d.code IN (:param_0, :param_1)" in artifact.sql
    assert artifact.parameters["param_0"] == "CSE"
    assert artifact.parameters["param_1"] == "ECE"
    assert "GROUP BY d.code" in artifact.sql


def test_compile_trend_query_by_term(compiler, principal_user):
    """Compiles TREND_QUERY over academic terms."""
    intent = StructuredIntent(
        intent_type=IntentType.TREND_QUERY,
        metric_id="attendance.percentage",
        dimensions=["term"],
    )
    artifact = compiler.compile(intent=intent, principal=principal_user)

    assert "t.label AS term" in artifact.sql
    assert "GROUP BY t.label" in artifact.sql
    assert "ORDER BY t.label ASC" in artifact.sql


def test_compile_ranking_query_top_departments(compiler, principal_user):
    """Compiles RANKING_QUERY with custom limit."""
    intent = StructuredIntent(
        intent_type=IntentType.RANKING_QUERY,
        metric_id="assessment.course_pass_percentage",
        dimensions=["department"],
        filters={"limit": 5},
    )
    artifact = compiler.compile(intent=intent, principal=principal_user)

    assert "ORDER BY metric_value DESC" in artifact.sql
    assert "LIMIT 5" in artifact.sql
    assert artifact.limit == 5


# -------------------------------------------------------------------------
# Server-Side Authorization Scoping Tests
# -------------------------------------------------------------------------

def test_compile_student_role_injects_self_predicate(compiler, student_user):
    """Verifies student account gets auth_student_id predicate injected automatically."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
    )
    artifact = compiler.compile(intent=intent, principal=student_user)

    assert "a.student_id = :auth_student_id" in artifact.sql
    assert artifact.parameters["auth_student_id"] == "person-student-01"
    assert "a.student_id = :auth_student_id" in artifact.authorization_predicates


def test_compile_hod_role_injects_department_predicate(compiler, hod_cse_user):
    """Verifies HOD gets their assigned department scope injected automatically."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
    )
    artifact = compiler.compile(intent=intent, principal=hod_cse_user)

    assert "d.code = :auth_department_code" in artifact.sql
    assert artifact.parameters["auth_department_code"] == "CSE"
    assert "d.code = :auth_department_code" in artifact.authorization_predicates


def test_compile_hod_cross_department_scope_denied(compiler, hod_cse_user):
    """HOD of CSE requesting ECE department must fail closed with SQLAuthorizationError."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
        filters={"department": "ECE"},
    )
    with pytest.raises(SQLAuthorizationError) as exc_info:
        compiler.compile(intent=intent, principal=hod_cse_user)

    assert "outside assigned scope" in str(exc_info.value)


def test_compile_rejects_out_of_scope_intent(compiler, principal_user):
    """Non-query intent types are rejected at compile time."""
    intent = StructuredIntent(
        intent_type=IntentType.OUT_OF_SCOPE,
        metric_id="attendance.percentage",
    )
    with pytest.raises(SQLCompilationError):
        compiler.compile(intent=intent, principal=principal_user)


def test_compile_rejects_unknown_metric(compiler, principal_user):
    """Non-existent metric is rejected at compile time."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="fake.nonexistent_metric",
    )
    with pytest.raises(SQLCompilationError):
        compiler.compile(intent=intent, principal=principal_user)
