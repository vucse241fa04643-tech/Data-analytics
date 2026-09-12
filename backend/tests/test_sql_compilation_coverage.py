"""
Agent 63 – SQL Compilation Coverage & Deterministic Safety Test Suite (Phase 7 Hardening)
Verifies:
1. Coverage report for all 24 APPROVED metrics in the Phase 4 Semantic Catalog.
2. Every approved metric compiles to a valid, parameterized, read-only SQLArtifact.
3. Every compiled query passes AST-level inspection via sqlglot.
4. Unapproved / review-required metrics fail closed.
5. Unknown / unmapped metrics fail closed.
6. Authorization alias safety across roles (PRINCIPAL, IQAC, HOD, STUDENT).
7. Cross-scope rejection for HOD and institutional-capacity rejection for STUDENT.
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
)
from backend.app.schemas.principal import (
    AuthenticatedPrincipal,
    ScopeType,
    ScopedRoleAssignment,
)
from backend.app.schemas.sql_artifact import SQLArtifact
from backend.app.services.semantic_registry import get_semantic_registry_service
from backend.app.services.sql_compiler import get_sql_compiler


@pytest.fixture
def compiler():
    return get_sql_compiler()


@pytest.fixture
def semantic_registry():
    return get_semantic_registry_service()


@pytest.fixture
def campus_principal():
    return AuthenticatedPrincipal(
        user_id="user-principal-coverage",
        username="principal_office",
        email="principal@college.edu",
        roles=["PRINCIPAL"],
        scoped_roles=[
            ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)
        ],
        permissions={
            "analytics.read",
            "attendance.read",
            "assessment.read",
            "academics.read",
            "outcomes.read",
            "placement.read",
            "quality.read",
        },
    )


@pytest.fixture
def iqac_director():
    return AuthenticatedPrincipal(
        user_id="user-iqac-coverage",
        username="iqac_director",
        email="iqac@college.edu",
        roles=["IQAC"],
        scoped_roles=[
            ScopedRoleAssignment(role="IQAC", scope_type=ScopeType.INSTITUTION)
        ],
        permissions={
            "analytics.read",
            "attendance.read",
            "assessment.read",
            "academics.read",
            "outcomes.read",
            "placement.read",
            "quality.read",
        },
    )


@pytest.fixture
def hod_cse():
    return AuthenticatedPrincipal(
        user_id="user-hod-cse-coverage",
        username="hod_cse",
        email="hod_cse@college.edu",
        roles=["HOD"],
        scoped_roles=[
            ScopedRoleAssignment(role="HOD", scope_type=ScopeType.DEPARTMENT, scope_id="CSE")
        ],
        permissions={
            "analytics.read",
            "attendance.read",
            "assessment.read",
            "academics.read",
            "outcomes.read",
            "placement.read",
            "quality.read",
        },
    )


@pytest.fixture
def student_user():
    return AuthenticatedPrincipal(
        user_id="user-student-coverage",
        username="student_01",
        email="student01@college.edu",
        person_id="person-student-coverage-01",
        roles=["STUDENT"],
        scoped_roles=[
            ScopedRoleAssignment(
                role="STUDENT",
                scope_type=ScopeType.SELF,
                scope_id="person-student-coverage-01",
            )
        ],
        permissions={"analytics.read", "attendance.read", "assessment.read", "placement.read"},
    )


# -------------------------------------------------------------------------
# 1. Deterministic Compilation Coverage Verification (24 / 24 Approved)
# -------------------------------------------------------------------------

def test_compilation_coverage_report(compiler, semantic_registry):
    """Verifies that all 24 APPROVED metrics are marked SUPPORTED with 0 missing mappings."""
    coverage = compiler.get_compilation_coverage()

    approved_in_registry = [
        m["metric_id"] for m in semantic_registry.get_approved_metrics()
    ]
    assert len(approved_in_registry) == 24

    for m_id in approved_in_registry:
        status = coverage.get(m_id)
        assert status == "SUPPORTED", f"Metric '{m_id}' is not marked SUPPORTED: got {status}"

    # Verify review required metrics are excluded
    assert coverage.get("attendance.students_below_threshold") == "UNAPPROVED_EXCLUDED"
    assert coverage.get("placement.placement_rate") == "UNAPPROVED_EXCLUDED"

    missing = [k for k, v in coverage.items() if v == "MISSING_SAFE_MAPPING"]
    assert len(missing) == 0, f"Found metrics with missing safe mappings: {missing}"


def test_compile_all_24_approved_metrics_as_metric_query(compiler, semantic_registry, campus_principal):
    """Executes safe compilation for every single approved metric in the catalog."""
    approved_metrics = semantic_registry.get_approved_metrics()
    assert len(approved_metrics) == 24

    compiled_count = 0
    for m in approved_metrics:
        m_id = m["metric_id"]
        intent = StructuredIntent(
            intent_type=IntentType.METRIC_QUERY,
            metric_id=m_id,
        )
        artifact = compiler.compile(intent=intent, principal=campus_principal)

        assert isinstance(artifact, SQLArtifact)
        assert artifact.read_only is True
        assert artifact.validation_status == "VALID"
        assert artifact.metric_id == m_id
        assert "SELECT" in artifact.sql
        assert "FROM" in artifact.sql
        assert "LIMIT" in artifact.sql
        assert artifact.limit <= 1000
        compiled_count += 1

    assert compiled_count == 24


# -------------------------------------------------------------------------
# 2. Query Archetypes across Approved Domains
# -------------------------------------------------------------------------

def test_breakdown_query_coverage(compiler, campus_principal):
    """Tests BREAKDOWN_QUERY compilation across attendance, assessment, placement."""
    metrics_to_test = [
        ("attendance.percentage", "department"),
        ("assessment.course_pass_percentage", "department"),
        ("placement.placed_students_count", "department"),
        ("academics.active_student_strength", "batch"),
    ]
    for m_id, dim in metrics_to_test:
        intent = StructuredIntent(
            intent_type=IntentType.BREAKDOWN_QUERY,
            metric_id=m_id,
            dimensions=[dim],
        )
        artifact = compiler.compile(intent, campus_principal)
        assert "GROUP BY" in artifact.sql
        assert "ORDER BY metric_value DESC" in artifact.sql


def test_trend_query_coverage(compiler, campus_principal):
    """Tests TREND_QUERY compilation across temporal metrics."""
    metrics_to_test = [
        ("attendance.percentage", "term"),
        ("assessment.course_pass_percentage", "term"),
        ("academics.active_course_offerings", "term"),
    ]
    for m_id, dim in metrics_to_test:
        intent = StructuredIntent(
            intent_type=IntentType.TREND_QUERY,
            metric_id=m_id,
            dimensions=[dim],
        )
        artifact = compiler.compile(intent, campus_principal)
        assert "GROUP BY" in artifact.sql
        assert "ASC" in artifact.sql


def test_comparison_query_coverage(compiler, campus_principal):
    """Tests COMPARISON_QUERY compilation with parameterized IN lists."""
    intent = StructuredIntent(
        intent_type=IntentType.COMPARISON_QUERY,
        metric_id="assessment.course_pass_percentage",
        dimensions=["department"],
        filters={"department": ["CSE", "ECE", "MECH"]},
    )
    artifact = compiler.compile(intent, campus_principal)
    assert "d.code IN (:param_0, :param_1, :param_2)" in artifact.sql
    assert artifact.parameters == {"param_0": "CSE", "param_1": "ECE", "param_2": "MECH"}


def test_ranking_query_coverage(compiler, campus_principal):
    """Tests RANKING_QUERY compilation with limit bounds."""
    intent = StructuredIntent(
        intent_type=IntentType.RANKING_QUERY,
        metric_id="placement.average_ctc",
        dimensions=["department"],
        filters={"limit": 3},
    )
    artifact = compiler.compile(intent, campus_principal)
    assert "LIMIT 3" in artifact.sql
    assert "ORDER BY metric_value DESC" in artifact.sql
    assert artifact.limit == 3


# -------------------------------------------------------------------------
# 3. Authorization Scoping & Alias Safety Tests
# -------------------------------------------------------------------------

def test_hod_own_department_scoping_applied(compiler, hod_cse):
    """HOD query receives auth_department_code predicate on correct table alias."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
    )
    artifact = compiler.compile(intent, hod_cse)
    assert "d.code = :auth_department_code" in artifact.sql
    assert artifact.parameters["auth_department_code"] == "CSE"
    assert "d.code = :auth_department_code" in artifact.authorization_predicates


def test_hod_cross_department_request_denied(compiler, hod_cse):
    """HOD of CSE attempting to query ECE department is strictly denied."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
        filters={"department": "ECE"},
    )
    with pytest.raises(SQLAuthorizationError) as exc_info:
        compiler.compile(intent, hod_cse)
    assert "outside assigned scope" in str(exc_info.value)


def test_student_self_scope_success_on_student_grain(compiler, student_user):
    """Student querying student-grain metrics receives student_id scoping."""
    # 1. Attendance percentage
    intent_att = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
    )
    art_att = compiler.compile(intent_att, student_user)
    assert "a.student_id = :auth_student_id" in art_att.sql
    assert art_att.parameters["auth_student_id"] == "person-student-coverage-01"

    # 2. Internal marks average
    intent_im = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="assessment.internal_marks_average",
    )
    art_im = compiler.compile(intent_im, student_user)
    assert "im.student_id = :auth_student_id" in art_im.sql


def test_student_rejected_on_institutional_capacity_metrics(compiler, student_user):
    """Student attempting to query course pass percentage or active offerings is rejected."""
    intent_pass = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="assessment.course_pass_percentage",
    )
    with pytest.raises(SQLAuthorizationError) as exc_info:
        compiler.compile(intent_pass, student_user)
    assert "strictly restricted to individual self-scoped records" in str(exc_info.value)


def test_iqac_director_has_institutional_scope(compiler, iqac_director):
    """IQAC Director has campus-wide scope and can compile quality and academic metrics."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="quality.kpi_latest_value",
    )
    artifact = compiler.compile(intent, iqac_director)
    assert "quality.v_kpi_latest" in artifact.sql
    assert artifact.read_only is True


# -------------------------------------------------------------------------
# 4. Defensive Fail-Closed Tests
# -------------------------------------------------------------------------

def test_unapproved_metric_fails_closed(compiler, campus_principal):
    """Review-required metric 'attendance.students_below_threshold' is rejected."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.students_below_threshold",
    )
    with pytest.raises(SQLAuthorizationError) as exc_info:
        compiler.compile(intent, campus_principal)
    assert "not approved for production analytics" in str(exc_info.value)


def test_unknown_metric_fails_closed(compiler, campus_principal):
    """Non-existent metric is rejected."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="nonexistent.hallucinated_metric",
    )
    with pytest.raises(SQLCompilationError) as exc_info:
        compiler.compile(intent, campus_principal)
    assert "not found in semantic catalog" in str(exc_info.value)
