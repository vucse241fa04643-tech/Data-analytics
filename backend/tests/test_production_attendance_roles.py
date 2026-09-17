"""
Agent 63 – Production Attendance Verification Suite for All Roles
Verifies that natural language attendance inquiries for all supported roles:
- COUNSELLOR (1-8)
- HOD (9-12)
- STUDENT (13-15)
- PRINCIPAL/MANAGEMENT (16)
map to correct intent, correct metric, correct scope, correct filters,
correct SQL/result shape, and correct authorization with zero unauthorized data leakage.
"""

import pytest
from backend.app.schemas.intent import IntentRequest, IntentType, IntentValidationStatus
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopedRoleAssignment, ScopeType
from backend.app.schemas.query_result import QueryResultStatus
from backend.app.services.execution_service import execution_service
from backend.app.services.identity_repository import reset_identity_repository
from backend.app.services.intent_service import get_intent_service
from backend.app.services.sql_compiler import get_sql_compiler
from backend.tests.test_counsellor_authorization import _make_counsellor


@pytest.fixture(autouse=True)
def reset_repo():
    reset_identity_repository()
    yield
    reset_identity_repository()


@pytest.fixture
def intent_service():
    return get_intent_service()


@pytest.fixture
def compiler():
    return get_sql_compiler()


@pytest.fixture
def counsellor_user():
    return _make_counsellor()


@pytest.fixture
def hod_cse_user():
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000004",
        username="test_hod_cse",
        email="hod_cse@vignan.ac.in",
        roles=["HOD"],
        scoped_roles=[
            ScopedRoleAssignment(
                role="HOD",
                scope_type=ScopeType.DEPARTMENT,
                scope_id="dept-cse-001",
            )
        ],
        permissions={"attendance.read"},
    )


@pytest.fixture
def student_user():
    return AuthenticatedPrincipal(
        user_id="bfc1067c-23c1-4776-958e-2f6e8918aaf5",
        username="test_student_1",
        email="test_student_1@vignan.ac.in",
        person_id="a6300000-0020-4000-8000-000000000001",
        roles=["STUDENT"],
        scoped_roles=[
            ScopedRoleAssignment(
                role="STUDENT",
                scope_type=ScopeType.SELF,
                scope_id="a6300000-0020-4000-8000-000000000001",
            )
        ],
        permissions={"attendance.read"},
    )


@pytest.fixture
def principal_user():
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[
            ScopedRoleAssignment(
                role="PRINCIPAL",
                scope_type=ScopeType.INSTITUTION,
                scope_id="inst-001",
            )
        ],
        permissions={"attendance.read", "analytics.read"},
    )


# =========================================================================
# COUNSELLOR TESTS (1-8)
# =========================================================================

def test_1_counsellor_average_attendance(intent_service, compiler, counsellor_user):
    """1. 'What is the average attendance of my students?' -> aggregate percentage"""
    req = IntentRequest(message="What is the average attendance of my students?")
    resp = intent_service.interpret_intent(req, principal=counsellor_user)
    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent.metric_id == "attendance.percentage"
    assert resp.intent.intent_type in (IntentType.METRIC_QUERY, IntentType.DIRECT_METRIC)
    assert resp.intent.dimensions in ([], None)

    art = compiler.compile(resp.intent, principal=counsellor_user)
    res = execution_service.execute_artifact(art, principal=counsellor_user)
    assert res.status == QueryResultStatus.SUCCESS
    assert res.row_count == 1
    assert float(res.rows[0]["metric_value"]) == pytest.approx(81.4, 0.1)


def test_2_counsellor_below_threshold_list(intent_service, compiler, counsellor_user):
    """2. 'Which of my students have attendance below 75%?' -> student-level filtered table"""
    req = IntentRequest(message="Which of my students have attendance below 75%?")
    resp = intent_service.interpret_intent(req, principal=counsellor_user)
    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent.metric_id == "attendance.percentage"
    assert resp.intent.intent_type == IntentType.THRESHOLD_QUERY
    assert "student" in resp.intent.dimensions
    assert resp.intent.threshold == 75.0
    assert resp.intent.operator == "<"

    art = compiler.compile(resp.intent, principal=counsellor_user)
    res = execution_service.execute_artifact(art, principal=counsellor_user)
    assert res.status in (QueryResultStatus.SUCCESS, QueryResultStatus.EMPTY)
    # Mentees of test_counsellor all have average attendance >= 79.67%, so 0 rows are strictly < 75%
    assert res.row_count == 0


def test_3_counsellor_below_threshold_count(intent_service, compiler, counsellor_user):
    """3. 'How many of my students have attendance below 75%?' -> count"""
    req = IntentRequest(message="How many of my students have attendance below 75%?")
    resp = intent_service.interpret_intent(req, principal=counsellor_user)
    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent.metric_id == "attendance.shortage_count"
    assert resp.intent.intent_type in (IntentType.DIRECT_METRIC, IntentType.METRIC_QUERY)

    art = compiler.compile(resp.intent, principal=counsellor_user)
    res = execution_service.execute_artifact(art, principal=counsellor_user)
    assert res.status == QueryResultStatus.SUCCESS
    assert res.row_count == 1
    assert isinstance(res.rows[0]["metric_value"], (int, float))


def test_4_counsellor_student_attendance_list(intent_service, compiler, counsellor_user):
    """4. 'List my students with their attendance percentage.' -> student-level table"""
    req = IntentRequest(message="List my students with their attendance percentage.")
    resp = intent_service.interpret_intent(req, principal=counsellor_user)
    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent.metric_id == "attendance.percentage"
    assert resp.intent.intent_type == IntentType.BREAKDOWN_QUERY
    assert "student" in resp.intent.dimensions

    art = compiler.compile(resp.intent, principal=counsellor_user)
    res = execution_service.execute_artifact(art, principal=counsellor_user)
    assert res.status == QueryResultStatus.SUCCESS
    assert res.row_count == 6
    assert "student" in res.rows[0]
    assert "metric_value" in res.rows[0]


def test_5_counsellor_attendance_details(intent_service, compiler, counsellor_user):
    """5. 'Give me attendance details of my assigned students.' -> detailed/student-level result"""
    req = IntentRequest(message="Give me attendance details of my assigned students.")
    resp = intent_service.interpret_intent(req, principal=counsellor_user)
    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent.metric_id == "attendance.percentage"
    assert resp.intent.intent_type == IntentType.BREAKDOWN_QUERY
    assert "student" in resp.intent.dimensions

    art = compiler.compile(resp.intent, principal=counsellor_user)
    res = execution_service.execute_artifact(art, principal=counsellor_user)
    assert res.status == QueryResultStatus.SUCCESS
    assert res.row_count == 6


def test_6_counsellor_lowest_attendance(intent_service, compiler, counsellor_user):
    """6. 'Who has the lowest attendance among my students?' -> authorized student-level result"""
    req = IntentRequest(message="Who has the lowest attendance among my students?")
    resp = intent_service.interpret_intent(req, principal=counsellor_user)
    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent.metric_id == "attendance.percentage"
    assert resp.intent.intent_type == IntentType.RANKING_QUERY
    assert resp.intent.order == "asc"
    assert "student" in resp.intent.dimensions

    art = compiler.compile(resp.intent, principal=counsellor_user)
    res = execution_service.execute_artifact(art, principal=counsellor_user)
    assert res.status == QueryResultStatus.SUCCESS
    assert res.row_count == 1
    assert res.rows[0]["student"] == "22CSEA005"
    assert float(res.rows[0]["metric_value"]) == pytest.approx(79.67, 0.1)


def test_7_counsellor_show_all_students_denied(intent_service, counsellor_user):
    """7. 'Show all students in the college.' -> denied"""
    req = IntentRequest(message="Show all students in the college.")
    resp = intent_service.interpret_intent(req, principal=counsellor_user)
    assert resp.status in (IntentValidationStatus.REJECTED, IntentValidationStatus.OUT_OF_SCOPE)


def test_8_counsellor_show_ece_attendance_denied(intent_service, counsellor_user):
    """8. 'Show ECE attendance.' -> denied"""
    req = IntentRequest(message="Show ECE attendance.")
    resp = intent_service.interpret_intent(req, principal=counsellor_user)
    assert resp.status in (IntentValidationStatus.REJECTED, IntentValidationStatus.OUT_OF_SCOPE)


# =========================================================================
# HOD TESTS (9-12)
# =========================================================================

def test_9_hod_average_attendance_my_department(intent_service, compiler, hod_cse_user):
    """9. 'What is the average attendance in my department?' -> allowed (CSE, 82.02%)"""
    req = IntentRequest(message="What is the average attendance in my department?")
    resp = intent_service.interpret_intent(req, principal=hod_cse_user)
    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent.metric_id == "attendance.percentage"

    art = compiler.compile(resp.intent, principal=hod_cse_user)
    res = execution_service.execute_artifact(art, principal=hod_cse_user)
    assert res.status == QueryResultStatus.SUCCESS
    assert res.row_count == 1
    assert float(res.rows[0]["metric_value"]) == pytest.approx(82.02, 0.1)


def test_10_hod_average_attendance_cse(intent_service, compiler, hod_cse_user):
    """10. 'What is the average attendance in CSE?' -> allowed (CSE, 82.02%)"""
    req = IntentRequest(message="What is the average attendance in CSE?")
    resp = intent_service.interpret_intent(req, principal=hod_cse_user)
    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent.metric_id == "attendance.percentage"

    art = compiler.compile(resp.intent, principal=hod_cse_user)
    res = execution_service.execute_artifact(art, principal=hod_cse_user)
    assert res.status == QueryResultStatus.SUCCESS
    assert res.row_count == 1
    assert float(res.rows[0]["metric_value"]) == pytest.approx(82.02, 0.1)


def test_11_hod_average_attendance_ece_denied(intent_service, hod_cse_user):
    """11. 'What is the average attendance in ECE?' -> denied"""
    req = IntentRequest(message="What is the average attendance in ECE?")
    resp = intent_service.interpret_intent(req, principal=hod_cse_user)
    assert resp.status in (IntentValidationStatus.REJECTED, IntentValidationStatus.OUT_OF_SCOPE)


def test_12_hod_average_attendance_across_institution_denied(intent_service, hod_cse_user):
    """12. 'What is the average attendance across the institution?' -> denied"""
    req = IntentRequest(message="What is the average attendance across the institution?")
    resp = intent_service.interpret_intent(req, principal=hod_cse_user)
    assert resp.status in (IntentValidationStatus.REJECTED, IntentValidationStatus.OUT_OF_SCOPE)


# =========================================================================
# STUDENT TESTS (13-15)
# =========================================================================

def test_13_student_what_is_my_attendance(intent_service, compiler, student_user):
    """13. 'What is my attendance?' -> own data (82.17%)"""
    req = IntentRequest(message="What is my attendance?")
    resp = intent_service.interpret_intent(req, principal=student_user)
    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent.metric_id == "attendance.percentage"
    assert resp.intent.filters.get("student_id") == "SELF"

    art = compiler.compile(resp.intent, principal=student_user)
    res = execution_service.execute_artifact(art, principal=student_user)
    assert res.status == QueryResultStatus.SUCCESS
    assert res.row_count == 1
    assert float(res.rows[0]["metric_value"]) == pytest.approx(82.17, 0.1)


def test_14_student_show_my_attendance_details(intent_service, compiler, student_user):
    """14. 'Show my attendance details.' -> own course-wise attendance breakdown"""
    req = IntentRequest(message="Show my attendance details.")
    resp = intent_service.interpret_intent(req, principal=student_user)
    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent.metric_id == "attendance.percentage"
    assert "course" in resp.intent.dimensions
    assert resp.intent.filters.get("student_id") == "SELF"

    art = compiler.compile(resp.intent, principal=student_user)
    res = execution_service.execute_artifact(art, principal=student_user)
    assert res.status == QueryResultStatus.SUCCESS
    assert res.row_count == 12
    assert "course" in res.rows[0]
    assert "metric_value" in res.rows[0]


def test_15_student_show_all_students_attendance_denied(intent_service, student_user):
    """15. 'Show all students\' attendance.' -> denied"""
    req = IntentRequest(message="Show all students' attendance.")
    resp = intent_service.interpret_intent(req, principal=student_user)
    assert resp.status in (IntentValidationStatus.REJECTED, IntentValidationStatus.OUT_OF_SCOPE)


# =========================================================================
# PRINCIPAL / MANAGEMENT TEST (16)
# =========================================================================

def test_16_principal_institution_wide_attendance(intent_service, compiler, principal_user):
    """16. Test existing institution-wide supported attendance query -> allowed (79.43%)"""
    req = IntentRequest(message="What is the average attendance across the institution?")
    resp = intent_service.interpret_intent(req, principal=principal_user)
    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent.metric_id == "attendance.percentage"

    art = compiler.compile(resp.intent, principal=principal_user)
    res = execution_service.execute_artifact(art, principal=principal_user)
    assert res.status == QueryResultStatus.SUCCESS
    assert res.row_count == 1
    assert float(res.rows[0]["metric_value"]) == pytest.approx(79.43, 0.1)
