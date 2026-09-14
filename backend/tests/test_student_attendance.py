"""
Agent 63 – S2: Student Self-Scoped Attendance Capability Tests
Comprehensive test suite verifying:
A. Self attendance queries ("Show my attendance", "What is my average attendance?", "What is my attendance percentage?")
B. Subject-wise self attendance ("Show my subject-wise attendance", "Show my attendance by subject")
C. Attendance shortage / low attendance and threshold filters
D. Term / Academic year filters ("Show my attendance this semester", "Show my attendance for 2025-26")
E. Negative security tests (cannot request another student, cohort, classmates, or override identity)
F. Principal isolation (test_student_1: 82.17%, test_student_2: 83.67%)
G. SQL safety (AST validation, parameterized values, no SELECT *)
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.errors import SQLAuthorizationError
from backend.app.main import app
from backend.app.schemas.intent import IntentType
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopeType, ScopedRoleAssignment
from backend.app.services.authorization import get_authorization_service
from backend.app.services.intent_service import get_intent_service
from backend.app.services.sql_compiler import get_sql_compiler
from backend.app.services.sql_validator import get_sql_validator

client = TestClient(app)


def get_token_for(username: str) -> str:
    """Helper to acquire valid JWT for a test user."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "InstitutionalSecurePass123!"},
    )
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]


# =========================================================================
# A. SELF ATTENDANCE INTENT & END-TO-END TESTS
# =========================================================================

@pytest.mark.parametrize("query_text", [
    "Show my attendance",
    "What is my average attendance?",
    "What is my attendance percentage?",
])
def test_student_overall_attendance_intent(query_text: str):
    """Verify that canonical student overall attendance phrasings resolve to METRIC_QUERY on attendance.percentage."""
    intent_service = get_intent_service()
    principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000010",
        username="test_student_1",
        email="221fa04001@vignan.ac.in",
        person_id="a6300000-0020-4000-8000-000000000001",
        roles=["STUDENT"],
        scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF, scope_id="a6300000-0020-4000-8000-000000000001")],
        permissions={"attendance.read"},
    )
    intent = intent_service._recognize_student_attendance_intent(query_text, principal)
    assert intent is not None, f"Failed to recognize intent for: {query_text}"
    assert intent.intent_type == IntentType.METRIC_QUERY
    assert intent.primary_metric_id == "attendance.percentage"
    assert intent.filters.get("student_id") == "SELF"


@pytest.mark.parametrize("query_text", [
    "Show my attendance",
    "What is my average attendance?",
    "What is my attendance percentage?",
    "what is my average attendance percentage",
])
def test_student_overall_attendance_api(query_text: str):
    """Verify end-to-end execution for test_student_1 returns exact attendance 82.17% with Student SELF scope."""
    token = get_token_for("test_student_1")
    resp = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": query_text},
    )
    assert resp.status_code == 200, f"Query failed: {resp.text}"
    data = resp.json()
    assert data["result"]["status"] == "SUCCESS"
    rows = data["result"]["rows"]
    assert len(rows) == 1
    val = float(rows[0]["metric_value"])
    assert val == 82.17, f"Expected 82.17% attendance for test_student_1, got {val}%"
    assert "Attendance Percentage" in data["metric_display_name"]
    assert data["visualization"]["unit"] == "%"
    assert "Single-value institutional KPI" not in str(data["visualization"])
    assert data.get("scope", {}).get("display") == "Student SELF"
    assert data.get("scope", {}).get("scope_type") == "SELF"


# =========================================================================
# B. SUBJECT-WISE SELF ATTENDANCE
# =========================================================================

@pytest.mark.parametrize("query_text", [
    "Show my subject-wise attendance",
    "Show my subject wise attendance",
    "Show my attendance by subject",
    "What is my attendance by subject",
    "Give my subject wise attendance",
    "What is my subject wise attendance",
    "Display my subject wise attendance",
    "Display my subject-wise attendance",
    "Give my subject-wise attendance",
    "Attendance by course",
    "Course-wise attendance",
    "Course wise attendance",
])
def test_student_subject_wise_attendance_intent(query_text: str):
    """Verify natural variants of subject-wise attendance resolve to BREAKDOWN_QUERY grouped by course."""
    intent_service = get_intent_service()
    principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000010",
        username="test_student_1",
        email="221fa04001@vignan.ac.in",
        person_id="a6300000-0020-4000-8000-000000000001",
        roles=["STUDENT"],
        scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF, scope_id="a6300000-0020-4000-8000-000000000001")],
        permissions={"attendance.read"},
    )
    intent = intent_service._recognize_student_attendance_intent(query_text, principal)
    assert intent is not None, f"Failed to recognize intent for: {query_text}"
    assert intent.intent_type == IntentType.BREAKDOWN_QUERY
    assert intent.primary_metric_id == "attendance.percentage"
    assert "course" in intent.dimensions
    assert intent.filters.get("student_id") == "SELF"


@pytest.mark.parametrize("query_text", [
    "Show my subject-wise attendance",
    "Show my subject wise attendance",
    "Show my attendance by subject",
    "What is my attendance by subject",
    "Give my subject wise attendance",
])
def test_student_subject_wise_attendance_api(query_text: str):
    """
    Verify subject-wise attendance query returns 12 course records with accurate percentages,
    including CS204=93%, CS404=92%, CS301=70%, CS303=70%, and correct Student SELF metadata.
    """
    token = get_token_for("test_student_1")
    resp = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": query_text},
    )
    assert resp.status_code == 200, f"Query failed: {resp.text}"
    data = resp.json()
    assert data["result"]["status"] == "SUCCESS"
    rows = data["result"]["rows"]
    assert len(rows) == 12, f"Expected 12 course records, got {len(rows)}"

    course_map = {}
    for r in rows:
        assert "course" in r
        assert "metric_value" in r
        val = float(r["metric_value"])
        assert 0.0 <= val <= 100.0
        course_map[r["course"]] = val

    # Verify expected course records
    assert course_map.get("CS204") == 93.0
    assert course_map.get("CS404") == 92.0
    assert course_map.get("CS301") == 70.0
    assert course_map.get("CS303") == 70.0

    # Verify result metadata and scope representation
    assert data["metric_display_name"] == "Student SELF / Subject-wise Attendance"
    assert data["visualization"]["title"] == "Student SELF / Subject-wise Attendance"
    assert "Single-value institutional KPI" not in str(data["visualization"])
    assert data.get("scope", {}).get("display") == "Student SELF"
    assert data.get("scope", {}).get("scope_type") == "SELF"
    assert "Institutional" not in str(data.get("scope", {}))


# =========================================================================
# C. ATTENDANCE FILTERS & SHORTAGE
# =========================================================================

@pytest.mark.parametrize("query_text", [
    "Which subjects have low attendance?",
    "Which subjects am I short of attendance in?",
])
def test_student_low_attendance_api(query_text: str):
    """Verify low attendance / shortage query returns the 2 seeded watch courses CS301 and CS303."""
    token = get_token_for("test_student_1")
    resp = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": query_text},
    )
    assert resp.status_code == 200, f"Query failed: {resp.text}"
    data = resp.json()
    assert data["result"]["status"] == "SUCCESS"
    rows = data["result"]["rows"]
    assert len(rows) == 2, f"Expected 2 courses with low attendance, got {len(rows)}"
    returned_courses = {r["course"] for r in rows}
    assert "CS301" in returned_courses
    assert "CS303" in returned_courses
    for r in rows:
        assert float(r["metric_value"]) == 70.0


def test_student_numeric_threshold_query_api():
    """Verify student query with parameterized numeric threshold."""
    token = get_token_for("test_student_1")
    resp = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Which of my subjects are below 60%?"},
    )
    assert resp.status_code == 200, f"Query failed: {resp.text}"
    data = resp.json()
    assert data["result"]["status"] in ("SUCCESS", "EMPTY")
    # All courses for test_student_1 are >= 70%, so 0 courses below 60%
    rows = data["result"]["rows"]
    assert len(rows) == 0


# =========================================================================
# D. TERM / ACADEMIC-YEAR FILTERS
# =========================================================================

def test_student_active_semester_attendance_api():
    """Verify attendance for active semester returns 84.00%."""
    token = get_token_for("test_student_1")
    resp = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Show my attendance this semester"},
    )
    assert resp.status_code == 200, f"Query failed: {resp.text}"
    data = resp.json()
    assert data["result"]["status"] == "SUCCESS"
    rows = data["result"]["rows"]
    assert len(rows) == 1
    val = float(rows[0]["metric_value"])
    assert val == 84.00, f"Expected 84.00% for active semester, got {val}%"


def test_student_academic_year_attendance_api():
    """Verify attendance for academic year 2025-26 returns 84.25%."""
    token = get_token_for("test_student_1")
    resp = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Show my attendance for 2025-26"},
    )
    assert resp.status_code == 200, f"Query failed: {resp.text}"
    data = resp.json()
    assert data["result"]["status"] == "SUCCESS"
    rows = data["result"]["rows"]
    assert len(rows) == 1
    val = float(rows[0]["metric_value"])
    assert val == 84.25, f"Expected 84.25% for 2025-26, got {val}%"


# =========================================================================
# E. NEGATIVE & SECURITY BOUNDARY TESTS
# =========================================================================

@pytest.mark.parametrize("denied_query", [
    "Show Deepak Kumar's attendance",
    "Show 22CSEB001 attendance",
    "Show all CSE students attendance",
    "Show attendance of my classmates",
    "Show all students below 75% attendance",
])
def test_student_cannot_query_other_students_or_cohort(denied_query: str):
    """Students attempting cross-student or cohort attendance enumeration receive HTTP 403."""
    token = get_token_for("test_student_2")
    resp = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": denied_query},
    )
    assert resp.status_code == 403, f"Expected 403 for '{denied_query}', got {resp.status_code}: {resp.text}"


def test_student_cannot_override_identity_with_roll_no_in_payload():
    """Student cannot bypass self scoping by injecting another roll number."""
    token = get_token_for("test_student_1")
    # Even if client passes a prompt attempting to ask about another roll number
    resp = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Show 22CSEB001 attendance"},
    )
    assert resp.status_code == 403


# =========================================================================
# F. AUTHORIZATION & PRINCIPAL ISOLATION
# =========================================================================

def test_student_identity_isolation_between_test_students():
    """Verify test_student_1 gets 82.17% and test_student_2 gets 83.67%."""
    token_1 = get_token_for("test_student_1")
    resp_1 = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token_1}"},
        json={"prompt": "Show my attendance"},
    )
    assert resp_1.status_code == 200
    val_1 = float(resp_1.json()["result"]["rows"][0]["metric_value"])
    assert val_1 == 82.17

    token_2 = get_token_for("test_student_2")
    resp_2 = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token_2}"},
        json={"prompt": "Show my attendance"},
    )
    assert resp_2.status_code == 200
    val_2 = float(resp_2.json()["result"]["rows"][0]["metric_value"])
    assert val_2 == 83.67

    # Distinct values proving proper database row isolation
    assert val_1 != val_2


# =========================================================================
# G. SQL SAFETY & COMPILER AST VALIDATION
# =========================================================================

def test_student_attendance_sql_safety():
    """Verify generated SQL contains no SELECT *, uses proper joins, and passes AST validator."""
    compiler = get_sql_compiler()
    validator = get_sql_validator()
    student_principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000010",
        username="test_student_1",
        email="221fa04001@vignan.ac.in",
        person_id="a6300000-0020-4000-8000-000000000001",
        roles=["STUDENT"],
        scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF, scope_id="a6300000-0020-4000-8000-000000000001")],
        permissions={"attendance.read"},
    )
    from backend.app.schemas.intent import StructuredIntent

    # Overall attendance intent
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
        primary_metric_id="attendance.percentage",
        filters={"student_id": "SELF"},
    )
    artifact = compiler.compile(intent, student_principal)

    assert "SELECT *" not in artifact.sql
    assert "a.student_id = :auth_student_id" in artifact.sql
    assert artifact.parameters.get("auth_student_id") == "a6300000-0021-4000-8000-000000000001"

    # AST validation must pass cleanly
    validated = validator.validate_artifact(artifact)
    assert validated.sql == artifact.sql

    # Subject-wise attendance intent
    breakdown_intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        metric_id="attendance.percentage",
        primary_metric_id="attendance.percentage",
        dimensions=["course"],
        filters={"student_id": "SELF"},
    )
    breakdown_artifact = compiler.compile(breakdown_intent, student_principal)
    assert "SELECT *" not in breakdown_artifact.sql
    assert "a.student_id = :auth_student_id" in breakdown_artifact.sql
    assert "GROUP BY" in breakdown_artifact.sql

    validated_bd = validator.validate_artifact(breakdown_artifact)
    assert validated_bd.sql == breakdown_artifact.sql


# =========================================================================
# H. PRODUCTION HARDENING — VERIFIED STUDENT IDENTITY RESOLUTION & FAIL CLOSED
# =========================================================================

def test_student_1_resolves_to_real_student_id():
    """
    Requirement 8: Proves test_student_1 resolves dynamically to its real database student_id
    (a6300000-0021-4000-8000-000000000001) via verified person_id -> people.student.student_id,
    with zero username-based logic.
    """
    compiler = get_sql_compiler()
    # Principal with arbitrary username but verified test_student_1 person_id
    principal = AuthenticatedPrincipal(
        user_id="arbitrary-user-id-001",
        username="arbitrary_student_username_x",
        email="student1@vignan.ac.in",
        person_id="a6300000-0020-4000-8000-000000000001",
        roles=["STUDENT"],
        scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF, scope_id="a6300000-0020-4000-8000-000000000001")],
        permissions={"attendance.read"},
    )
    from backend.app.schemas.intent import StructuredIntent

    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
        primary_metric_id="attendance.percentage",
        filters={"student_id": "SELF"},
    )
    artifact = compiler.compile(intent, principal)

    assert "a.student_id = :auth_student_id" in artifact.sql
    assert artifact.parameters.get("auth_student_id") == "a6300000-0021-4000-8000-000000000001"


def test_student_2_resolves_to_real_student_id():
    """
    Requirement 8: Proves test_student_2 resolves dynamically to its real database student_id
    (a6300000-0021-4000-8000-000000000002) via verified person_id -> people.student.student_id,
    with zero username-based logic.
    """
    compiler = get_sql_compiler()
    # Principal with arbitrary username but verified test_student_2 person_id
    principal = AuthenticatedPrincipal(
        user_id="arbitrary-user-id-002",
        username="arbitrary_student_username_y",
        email="student2@vignan.ac.in",
        person_id="a6300000-0020-4000-8000-000000000002",
        roles=["STUDENT"],
        scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF, scope_id="a6300000-0020-4000-8000-000000000002")],
        permissions={"attendance.read"},
    )
    from backend.app.schemas.intent import StructuredIntent

    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
        primary_metric_id="attendance.percentage",
        filters={"student_id": "SELF"},
    )
    artifact = compiler.compile(intent, principal)

    assert "a.student_id = :auth_student_id" in artifact.sql
    assert artifact.parameters.get("auth_student_id") == "a6300000-0021-4000-8000-000000000002"


def test_cross_student_access_denied_403():
    """
    Requirement 8: Proves cross-student access remains 403.
    Student 1 cannot request another student's attendance.
    """
    token = get_token_for("test_student_1")
    resp = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Show attendance for Manish Gupta"},
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


def test_payload_student_id_and_roll_no_tampering_ineffective():
    """
    Requirement 8: Proves payload student_id and roll_no tampering remains ineffective.
    Even if an intent contains malicious filter overrides, server-side scoping strictly binds
    to the authenticated principal's verified student_id.
    """
    compiler = get_sql_compiler()
    principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000010",
        username="test_student_1",
        email="221fa04001@vignan.ac.in",
        person_id="a6300000-0020-4000-8000-000000000001",
        roles=["STUDENT"],
        scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF, scope_id="a6300000-0020-4000-8000-000000000001")],
        permissions={"attendance.read"},
    )
    from backend.app.schemas.intent import StructuredIntent

    # Tampered intent filters attempting to inject another student's UUID and roll_no
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
        primary_metric_id="attendance.percentage",
        filters={
            "student_id": "a6300000-0021-4000-8000-000000000002",
            "roll_no": "22CSEB001",
        },
    )
    artifact = compiler.compile(intent, principal)

    # Scoping must strictly use principal 1's resolved student_id, NEVER the tampered payload values
    assert artifact.parameters["auth_student_id"] == "a6300000-0021-4000-8000-000000000001"
    assert "a6300000-0021-4000-8000-000000000002" not in artifact.parameters.values()
    assert "22CSEB001" not in artifact.parameters.values()


def test_unlinked_student_without_person_id_fails_closed():
    """
    Requirement 8: Proves an unlinked STUDENT with no person_id fails closed (SQLAuthorizationError).
    """
    compiler = get_sql_compiler()
    unlinked_principal = AuthenticatedPrincipal(
        user_id="unlinked-user-001",
        username="unlinked_student",
        email="unlinked@vignan.ac.in",
        person_id=None,
        roles=["STUDENT"],
        scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF)],
        permissions={"attendance.read"},
    )
    from backend.app.schemas.intent import StructuredIntent

    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
        primary_metric_id="attendance.percentage",
        filters={"student_id": "SELF"},
    )
    with pytest.raises(SQLAuthorizationError) as exc_info:
        compiler.compile(intent, unlinked_principal)
    assert "no verified student/person record linkage" in str(exc_info.value)


def test_unlinked_student_with_nonexistent_person_id_fails_closed():
    """
    Requirement 8: Proves an unlinked STUDENT with a person_id not found in people.student fails closed.
    """
    compiler = get_sql_compiler()
    unlinked_principal = AuthenticatedPrincipal(
        user_id="unlinked-user-002",
        username="phantom_student",
        email="phantom@vignan.ac.in",
        person_id="00000000-0000-0000-0000-999999999999",
        roles=["STUDENT"],
        scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF)],
        permissions={"attendance.read"},
    )
    from backend.app.schemas.intent import StructuredIntent

    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        metric_id="attendance.percentage",
        primary_metric_id="attendance.percentage",
        filters={"student_id": "SELF"},
    )
    with pytest.raises(SQLAuthorizationError) as exc_info:
        compiler.compile(intent, unlinked_principal)
    assert "no verified institutional student record linkage in people.student" in str(exc_info.value)
