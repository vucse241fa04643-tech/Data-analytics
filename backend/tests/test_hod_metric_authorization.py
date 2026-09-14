"""Agent 63 - Phase 8 / Regression Suite
Tests for HOD Analytical Metric Authorization and Scope Normalization:
- Verifies HOD department scope slug (e.g. 'dept-cse-001') is normalized to code ('CSE').
- Verifies duplicate user department filters are prevented when authorization predicate exists.
- Verifies HOD cross-department queries fail closed.
- Verifies unconstrained queries are automatically restricted to the HOD's assigned department.
- Verifies Principal and Student-list pipelines remain unaffected.
- Verifies conversation context cannot bypass HOD departmental boundaries.
"""

import pytest

from backend.app.core.errors import SQLAuthorizationError
from backend.app.schemas.conversation_context import ConversationContext
from backend.app.schemas.intent import IntentRequest, IntentType, IntentValidationStatus, StructuredIntent
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopeType, ScopedRoleAssignment
from backend.app.services.authentication import get_authentication_service
from backend.app.services.execution_service import execution_service
from backend.app.services.intent_service import get_intent_service
from backend.app.services.sql_compiler import get_sql_compiler, normalize_department_scope


@pytest.fixture
def auth_service():
    return get_authentication_service()


@pytest.fixture
def principal_user(auth_service):
    return auth_service.authenticate_user("test_principal", "InstitutionalSecurePass123!")


@pytest.fixture
def hod_cse_user(auth_service):
    return auth_service.authenticate_user("test_hod_cse", "InstitutionalSecurePass123!")


@pytest.fixture
def compiler():
    return get_sql_compiler()


def test_1_hod_cse_active_student_strength_returns_150(hod_cse_user, compiler):
    """HOD CSE querying CSE active student strength succeeds and returns 150."""
    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="academics.active_student_strength",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="Test HOD CSE student strength",
    )
    artifact = compiler.compile(intent, principal=hod_cse_user)
    assert artifact.parameters.get("auth_department_code") == "CSE"
    assert "param_0" not in artifact.parameters  # No duplicate filter
    res = execution_service.execute_artifact(artifact, principal=hod_cse_user)
    assert res.row_count == 1
    assert res.rows[0]["metric_value"] == 150


def test_2_hod_cse_average_attendance_returns_82_02(hod_cse_user, compiler):
    """HOD CSE querying CSE average attendance succeeds and returns ~82.02%."""
    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="Test HOD CSE attendance",
    )
    artifact = compiler.compile(intent, principal=hod_cse_user)
    assert artifact.parameters.get("auth_department_code") == "CSE"
    assert "param_0" not in artifact.parameters  # No duplicate filter
    res = execution_service.execute_artifact(artifact, principal=hod_cse_user)
    assert res.row_count == 1
    assert float(res.rows[0]["metric_value"]) == pytest.approx(82.02, 0.1)


def test_3_hod_cse_unconstrained_query_automatically_restricted_to_cse(hod_cse_user, compiler):
    """HOD CSE querying student strength without specifying a department is bounded to CSE."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="academics.active_student_strength",
        dimensions=[],
        filters={},
        reasoning_summary="Test HOD unconstrained student strength",
    )
    artifact = compiler.compile(intent, principal=hod_cse_user)
    assert artifact.parameters.get("auth_department_code") == "CSE"
    assert "d.code = :auth_department_code" in artifact.sql
    res = execution_service.execute_artifact(artifact, principal=hod_cse_user)
    assert res.rows[0]["metric_value"] == 150


def test_4_hod_cse_cross_department_ece_denied(hod_cse_user, compiler):
    """HOD CSE requesting ECE department metric query is rejected with SQLAuthorizationError."""
    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="academics.active_student_strength",
        dimensions=["department"],
        filters={"department": "ECE"},
        reasoning_summary="Test cross-department attempt",
    )
    with pytest.raises(SQLAuthorizationError) as excinfo:
        compiler.compile(intent, principal=hod_cse_user)
    assert "HOD authorization scope violation" in str(excinfo.value)


def test_5_hod_cse_sql_contains_single_department_restriction(hod_cse_user, compiler):
    """Generated SQL has exactly one department condition on d.code."""
    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="Test single restriction",
    )
    artifact = compiler.compile(intent, principal=hod_cse_user)
    # Check that WHERE clause contains exactly one condition on d.code
    where_part = artifact.sql.split("WHERE")[-1].split("GROUP BY")[0].split("ORDER BY")[0].split("LIMIT")[0]
    assert where_part.count("d.code") == 1
    assert "d.code = :auth_department_code" in where_part
    assert ":param_0" not in artifact.sql
    assert "param_0" not in artifact.parameters


def test_6_hod_authorization_parameter_is_cse_not_slug(hod_cse_user, compiler):
    """auth_department_code parameter must be 'CSE', never the raw scope ID 'dept-cse-001'."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="academics.active_student_strength",
        filters={},
    )
    artifact = compiler.compile(intent, principal=hod_cse_user)
    assert artifact.parameters["auth_department_code"] == "CSE"
    assert artifact.parameters["auth_department_code"] != "dept-cse-001"


def test_7_principal_cse_metric_unaffected(principal_user, compiler):
    """Principal + CSE query continues to work without injected HOD auth predicate."""
    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="academics.active_student_strength",
        dimensions=["department"],
        filters={"department": "CSE"},
    )
    artifact = compiler.compile(intent, principal=principal_user)
    assert "auth_department_code" not in artifact.parameters
    assert artifact.authorization_predicates == []
    res = execution_service.execute_artifact(artifact, principal=principal_user)
    assert res.rows[0]["metric_value"] == 150


def test_8_student_list_hod_behavior_remains_unchanged(hod_cse_user, compiler):
    """Student-list pipeline continues to return CSE students and reject ECE."""
    # 1. CSE list succeeds
    intent_cse = StructuredIntent(
        intent_type=IntentType.STUDENT_LIST,
        metric_id="student.list",
        primary_metric_id="student.list",
        student_filters={"department": "CSE"},
        filters={"department": "CSE"},
        page=1,
        page_size=25,
    )
    art_cse = compiler.compile(intent_cse, principal=hod_cse_user)
    assert art_cse.parameters.get("auth_department_code") == "CSE"
    res_cse = execution_service.execute_artifact(art_cse, principal=hod_cse_user)
    assert res_cse.row_count > 0

    # 2. ECE list denied
    intent_ece = StructuredIntent(
        intent_type=IntentType.STUDENT_LIST,
        metric_id="student.list",
        primary_metric_id="student.list",
        student_filters={"department": "ECE"},
        filters={"department": "ECE"},
        page=1,
        page_size=25,
    )
    with pytest.raises(SQLAuthorizationError):
        compiler.compile(intent_ece, principal=hod_cse_user)


def test_9_other_department_scope_normalization():
    """Test normalization of other departmental scope identifiers."""
    assert normalize_department_scope("dept-cse-001") == ("auth_department_code", "CSE")
    assert normalize_department_scope("dept-ece-002") == ("auth_department_code", "ECE")
    assert normalize_department_scope("dept-eee-001") == ("auth_department_code", "EEE")
    assert normalize_department_scope("dept-mech-004") == ("auth_department_code", "MECH")
    assert normalize_department_scope("dept-civil-005") == ("auth_department_code", "CIVIL")
    assert normalize_department_scope("CSE") == ("auth_department_code", "CSE")
    uuid_str = "a6300000-0003-4000-8000-000000000001"
    assert normalize_department_scope(uuid_str) == ("auth_department_id", uuid_str)


def test_10_conversation_context_cannot_bypass_hod_scope(hod_cse_user, compiler):
    """Conversation context carrying cross-department filters is rejected for HOD."""
    # Even if an intent inherits an ECE filter from prior context, the HOD compiler fails closed
    inherited_intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "ECE"},  # Inherited cross-department context
        reasoning_summary="Follow-up query with inherited department context",
    )
    with pytest.raises(SQLAuthorizationError) as excinfo:
        compiler.compile(inherited_intent, principal=hod_cse_user)
    assert "HOD authorization scope violation" in str(excinfo.value)


def test_11_hod_cse_show_students_in_my_department(hod_cse_user):
    """Scenario 1: 'Show students in my department' intent and query resolves strictly to CSE."""
    service = get_intent_service()
    req = IntentRequest(message="Show students in my department")
    resp = service.interpret_intent(req, principal=hod_cse_user)
    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent.intent_type == IntentType.STUDENT_LIST
    assert resp.intent.student_filters.get("department") == "CSE"

    compiler = get_sql_compiler()
    artifact = compiler.compile(resp.intent, principal=hod_cse_user)
    assert artifact.parameters.get("auth_department_code") == "CSE"
    res = execution_service.execute_artifact(artifact, principal=hod_cse_user)
    assert res.row_count == 25
    for row in res.rows:
        assert row.get("department_code") == "CSE"


def test_12_hod_cse_cross_dept_student_list_roll_number_denied(hod_cse_user):
    """Scenario 3 & 14: Cross-department student retrieval by foreign roll_no is denied."""
    from backend.app.services.authorization import get_authorization_service
    from backend.app.core.errors import AuthorizationError

    # Attempting to fetch an ECE student by roll_no
    intent = StructuredIntent(
        intent_type=IntentType.STUDENT_LIST,
        metric_id="student.list",
        primary_metric_id="student.list",
        student_filters={"roll_no": "ECE2022001"},
    )
    authz_service = get_authorization_service()
    decision = authz_service.authorize_student_list(principal=hod_cse_user, student_filters=intent.student_filters)
    assert not decision.allowed
    assert decision.reason_code == "SCOPE_OUT_OF_BOUNDS"


def test_13_hod_cse_course_wise_attendance_no_alias_collision(hod_cse_user, compiler):
    """Scenario 7 (Bug 2): 'Show course-wise attendance for CSE' executes with join deduplication."""
    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["course"],
        filters={"department": "CSE"},
        reasoning_summary="Course-wise attendance for CSE",
    )
    artifact = compiler.compile(intent, principal=hod_cse_user)
    assert artifact.sql.count("JOIN academics.course_offering co") == 1
    res = execution_service.execute_artifact(artifact, principal=hod_cse_user)
    assert res.row_count == 15
    for row in res.rows:
        assert "course" in row
        assert "metric_value" in row


def test_14_hod_cse_payload_tampering_department_code(hod_cse_user, compiler):
    """Scenario 8: Request payload tampering with department_code=ECE is denied."""
    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="academics.active_student_strength",
        dimensions=["department"],
        filters={"department": "ECE"},
    )
    with pytest.raises(SQLAuthorizationError) as excinfo:
        compiler.compile(intent, principal=hod_cse_user)
    assert "HOD authorization scope violation" in str(excinfo.value)


def test_15_hod_cse_payload_tampering_foreign_uuid(hod_cse_user, compiler):
    """Scenario 9: Request payload tampering with foreign department UUID is denied."""
    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="academics.active_student_strength",
        dimensions=["department"],
        filters={"department_id": "a6300000-0003-4000-8000-000000000002"},  # ECE UUID
    )
    with pytest.raises(SQLAuthorizationError) as excinfo:
        compiler.compile(intent, principal=hod_cse_user)
    assert "HOD authorization scope violation" in str(excinfo.value)


def test_16_inactive_hod_denied(compiler):
    """Scenario 11: Inactive HOD user fails closed."""
    inactive_hod = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000099",
        username="inactive_hod",
        email="inactive.hod@vignan.ac.in",
        roles=["HOD"],
        scoped_roles=[
            ScopedRoleAssignment(
                role="HOD",
                scope_type=ScopeType.DEPARTMENT,
                scope_id="dept-cse-001",
            )
        ],
        is_active=False,
    )
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="academics.active_student_strength",
        filters={},
    )
    with pytest.raises(SQLAuthorizationError) as exc:
        compiler.compile(intent, principal=inactive_hod)
    assert "Account is inactive" in str(exc.value)


def test_17_hod_missing_scope_fails_closed(compiler):
    """Scenario 12: HOD with missing department scope assignment fails closed."""
    unassigned_hod = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000098",
        username="unassigned_hod",
        email="unassigned.hod@vignan.ac.in",
        roles=["HOD"],
        permissions={"academics.read", "analytics.read"},
        scoped_roles=[],
        is_active=True,
    )
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="academics.active_student_strength",
        filters={},
    )
    with pytest.raises(SQLAuthorizationError) as exc:
        compiler.compile(intent, principal=unassigned_hod)
    assert "HOD account has no assigned departmental scope boundary" in str(exc.value)


def test_18_hod_confidential_schema_denied(hod_cse_user, compiler):
    """Scenario 13: Access to confidential HR/financial metrics is denied."""
    from backend.app.services.authorization import get_authorization_service
    authz_service = get_authorization_service()
    decision = authz_service.authorize_metric(
        metric_id="finance.tuition_collected",
        principal=hod_cse_user,
    )
    assert not decision.allowed
    assert decision.reason_code == "METRIC_NOT_FOUND"


def test_19_hod_cse_pass_percentage_for_ece_denied(hod_cse_user, compiler):
    """Scenario 6: HOD CSE asking pass percentage for ECE is denied."""
    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="assessment.course_pass_percentage",
        dimensions=["course"],
        filters={"department": "ECE"},
    )
    with pytest.raises(SQLAuthorizationError) as exc:
        compiler.compile(intent, principal=hod_cse_user)
    assert "HOD authorization scope violation" in str(exc.value)


def test_20_bug_1_students_with_low_attendance_controlled_rejection(hod_cse_user):
    """Scenario for Bug 1: 'Show students with low attendance in my department' fails closed with REVIEW_REQUIRED message."""
    service = get_intent_service()
    req = IntentRequest(message="Show students with low attendance in my department")
    resp = service.interpret_intent(req, principal=hod_cse_user)
    assert resp.status == IntentValidationStatus.REJECTED
    assert resp.clarification_questions == []
    assert "REVIEW_REQUIRED" in resp.message
