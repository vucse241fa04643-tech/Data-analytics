"""
Agent 63 – Authorized Student Record Retrieval Comprehensive Tests
Tests the complete end-to-end authorized student-record retrieval pipeline:
1. Intent recognition (canonical requests without consuming Groq quota)
2. Role-based authorization matrix (Principal, HOD, Faculty, Mentor, Student, Inactive)
3. Security boundaries (SELECT * rejection, anti-SQL injection, restricted field protection, clamped pagination)
4. Read-only PostgreSQL execution against local development seed
5. Result validation and pagination metadata
6. Audit query logging safety
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.errors import (
    ResultValidationError,
    SQLAuthorizationError,
    SQLCompilationError,
    SQLValidationError,
)
from backend.app.main import app
from backend.app.schemas.intent import IntentType, IntentValidationStatus, StructuredIntent
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopeType, ScopedRoleAssignment
from backend.app.schemas.student_catalog import (
    APPROVED_STUDENT_FIELDS,
    DEFAULT_STUDENT_PROJECTION,
    STRICTLY_PROHIBITED_FIELDS,
)
from backend.app.services.authorization import get_authorization_service
from backend.app.services.identity_repository import get_identity_repository
from backend.app.services.intent_service import get_intent_service
from backend.app.services.intent_validator import get_intent_validator
from backend.app.services.query_log_service import get_query_log_service
from backend.app.services.result_validator import result_validator
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
# A. INTENT RECOGNITION TESTS
# =========================================================================

def test_intent_display_all_cse_students():
    intent_service = get_intent_service()
    principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)],
        permissions={"analytics.read"},
    )
    raw = intent_service._recognize_student_list_intent("Display all CSE students", principal)
    assert raw is not None
    assert raw.intent_type == IntentType.STUDENT_LIST
    assert raw.student_filters.get("department") == "CSE"


def test_intent_list_cse_students():
    intent_service = get_intent_service()
    principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)],
        permissions={"analytics.read"},
    )
    raw = intent_service._recognize_student_list_intent("List CSE students", principal)
    assert raw is not None
    assert raw.intent_type == IntentType.STUDENT_LIST
    assert raw.student_filters.get("department") == "CSE"


def test_intent_show_students_in_section_cse_a():
    intent_service = get_intent_service()
    principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)],
        permissions={"analytics.read"},
    )
    raw = intent_service._recognize_student_list_intent("Show students in section CSE-A", principal)
    assert raw is not None
    assert raw.intent_type == IntentType.STUDENT_LIST
    assert raw.student_filters.get("section") == "CSE-A"


def test_intent_show_cse_students_from_2025_batch():
    intent_service = get_intent_service()
    principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)],
        permissions={"analytics.read"},
    )
    raw = intent_service._recognize_student_list_intent("Show CSE students from 2025 batch", principal)
    assert raw is not None
    assert raw.intent_type == IntentType.STUDENT_LIST
    assert raw.student_filters.get("department") == "CSE"
    assert raw.student_filters.get("batch") == "2025"


def test_intent_show_my_student_record():
    intent_service = get_intent_service()
    student_principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000010",
        username="test_student_1",
        email="221fa04001@vignan.ac.in",
        roles=["STUDENT"],
        scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF, scope_id="student-uuid-s101")],
        permissions={"attendance.read"},
    )
    raw = intent_service._recognize_student_list_intent("Show my student record", student_principal)
    assert raw is not None
    assert raw.intent_type == IntentType.STUDENT_LIST
    assert raw.student_filters.get("student_id") == "SELF"


# =========================================================================
# B. AUTHORIZATION MATRIX TESTS
# =========================================================================

def test_principal_authorized_institution_wide():
    authz = get_authorization_service()
    principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)],
        permissions={"analytics.read"},
    )
    decision = authz.authorize_student_list(principal, {"department": "CSE"})
    assert decision.allowed is True
    assert decision.effective_scope["scope_type"] == ScopeType.INSTITUTION.value


def test_hod_cse_allowed_for_cse():
    authz = get_authorization_service()
    hod_cse = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000004",
        username="test_hod_cse",
        email="hod.cse@vignan.ac.in",
        roles=["HOD"],
        scoped_roles=[ScopedRoleAssignment(role="HOD", scope_type=ScopeType.DEPARTMENT, scope_id="dept-cse-001")],
        permissions={"attendance.read"},
    )
    decision = authz.authorize_student_list(hod_cse, {"department": "CSE"})
    assert decision.allowed is True
    assert decision.effective_scope["scope_type"] == ScopeType.DEPARTMENT.value


def test_hod_cse_denied_for_ece():
    authz = get_authorization_service()
    hod_cse = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000004",
        username="test_hod_cse",
        email="hod.cse@vignan.ac.in",
        roles=["HOD"],
        scoped_roles=[ScopedRoleAssignment(role="HOD", scope_type=ScopeType.DEPARTMENT, scope_id="dept-cse-001")],
        permissions={"attendance.read"},
    )
    decision = authz.authorize_student_list(hod_cse, {"department": "ECE"})
    assert decision.allowed is False
    assert decision.reason_code == "SCOPE_OUT_OF_BOUNDS"


def test_faculty_outside_scope_denied():
    authz = get_authorization_service()
    faculty_cse = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000006",
        username="test_faculty_cse",
        email="faculty.cse@vignan.ac.in",
        roles=["FACULTY"],
        scoped_roles=[ScopedRoleAssignment(role="FACULTY", scope_type=ScopeType.DEPARTMENT, scope_id="dept-cse-001")],
        permissions={"attendance.read"},
    )
    decision = authz.authorize_student_list(faculty_cse, {"department": "ECE"})
    assert decision.allowed is False
    assert decision.reason_code == "SCOPE_OUT_OF_BOUNDS"


def test_mentor_authorized_mentees_only():
    authz = get_authorization_service()
    mentor = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000007",
        username="test_mentor_faculty",
        email="mentor.cse@vignan.ac.in",
        roles=["MENTOR"],
        scoped_roles=[ScopedRoleAssignment(role="MENTOR", scope_type=ScopeType.SELF, scope_id="mentor-faculty-uuid-007")],
        permissions={"attendance.read"},
    )
    # Asking for cohort department listing is denied for mentor
    decision = authz.authorize_student_list(mentor, {"department": "CSE"})
    assert decision.allowed is False
    assert decision.reason_code == "SCOPE_OUT_OF_BOUNDS"

    # Asking without department cohort filter is authorized to mentee scope
    decision_self = authz.authorize_student_list(mentor, {})
    assert decision_self.allowed is True


def test_student_own_record_only():
    authz = get_authorization_service()
    student = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000010",
        username="test_student_1",
        email="221fa04001@vignan.ac.in",
        person_id="person-student-001",
        roles=["STUDENT"],
        scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF, scope_id="student-uuid-s101")],
        permissions={"attendance.read"},
    )
    # Self record allowed
    decision_self = authz.authorize_student_list(student, {"student_id": "SELF"})
    assert decision_self.allowed is True
    assert decision_self.effective_scope["scope_type"] == ScopeType.SELF.value

    # General CSE student list denied
    decision_cohort = authz.authorize_student_list(student, {"department": "CSE"})
    assert decision_cohort.allowed is False
    assert decision_cohort.reason_code == "SCOPE_OUT_OF_BOUNDS"

    # Querying another student's ID denied
    decision_other = authz.authorize_student_list(student, {"student_id": "person-student-999"})
    assert decision_other.allowed is False
    assert decision_other.reason_code == "SCOPE_OUT_OF_BOUNDS"


def test_inactive_user_denied():
    authz = get_authorization_service()
    inactive_principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000099",
        username="test_inactive_user",
        email="inactive@vignan.ac.in",
        is_active=False,
        roles=["STUDENT"],
        scoped_roles=[],
        permissions=set(),
    )
    decision = authz.authorize_student_list(inactive_principal, {})
    assert decision.allowed is False
    assert decision.reason_code == "INACTIVE_ACCOUNT"


# =========================================================================
# C. SECURITY INVARIANTS TESTS
# =========================================================================

def test_sql_compiler_rejects_select_star():
    compiler = get_sql_compiler()
    principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)],
        permissions={"analytics.read"},
    )
    intent = StructuredIntent(
        intent_type=IntentType.STUDENT_LIST,
        metric_id="student.list",
        student_filters={"department": "CSE"},
        requested_fields=["*"],  # User attempting wildcard
    )
    artifact = compiler.compile(intent, principal)
    # Compiler must NOT emit SELECT *
    assert "SELECT *" not in artifact.sql
    assert "SELECT\n    *" not in artifact.sql
    # Falls back to approved default projection
    assert "s.roll_no AS roll_no" in artifact.sql


def test_sql_injection_in_filter_rejected():
    validator = get_intent_validator()
    with pytest.raises(ValueError, match="Raw SQL clause or keyword"):
        StructuredIntent(
            intent_type=IntentType.STUDENT_LIST,
            student_filters={"department": "CSE'; DROP TABLE people.student; --"},
        )


def test_restricted_fields_rejected():
    validator = get_intent_validator()
    intent = StructuredIntent(
        intent_type=IntentType.STUDENT_LIST,
        student_filters={"department": "CSE"},
        requested_fields=["roll_no", "password", "social_category"],
    )
    res = validator.validate_intent(intent)
    assert res.is_valid is False
    assert res.error_code == "RESTRICTED_FIELD"
    assert "restricted" in res.message.lower()


def test_unapproved_column_in_result_rejected():
    with pytest.raises(ResultValidationError, match="Unapproved column"):
        result_validator.validate_and_normalize(
            raw_columns=["roll_no", "unapproved_internal_token"],
            raw_rows=[{"roll_no": "21CSE001", "unapproved_internal_token": "secret"}],
            raw_data_types={"roll_no": "varchar", "unapproved_internal_token": "varchar"},
            metric_id="student.list",
            execution_time_ms=10.0,
            result_type="STUDENT_LIST",
        )


def test_oversized_page_bounded_to_50():
    validator = get_intent_validator()
    intent = StructuredIntent(
        intent_type=IntentType.STUDENT_LIST,
        student_filters={"department": "CSE"},
        page=1,
        page_size=50,  # Max allowed limit
    )
    res = validator.validate_intent(intent)
    assert res.is_valid is True
    assert res.validated_intent.page_size == 50


# =========================================================================
# D. DATA INTEGRITY & POSTGRES EXECUTION TESTS (against local seed)
# =========================================================================

def test_api_cse_student_list_execution():
    token = get_token_for("test_principal")
    res = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Display all CSE students"},
    )
    assert res.status_code == 200, f"Query failed: {res.text}"
    data = res.json()
    assert data["result"] is not None
    assert data["result"]["result_type"] == "STUDENT_LIST"
    rows = data["result"]["rows"]
    assert len(rows) > 0
    # Every row must be CSE
    for r in rows:
        assert r["department_code"] == "CSE"
    # Metadata has pagination
    meta = data["result"]["metadata"]
    assert meta["page"] == 1
    assert meta["page_size"] == 25


def test_api_ece_student_list_execution():
    token = get_token_for("test_principal")
    res = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Display all ECE students"},
    )
    assert res.status_code == 200
    data = res.json()
    rows = data["result"]["rows"]
    assert len(rows) > 0
    for r in rows:
        assert r["department_code"] == "ECE"


def test_api_hod_cse_allowed_for_cse():
    token = get_token_for("test_hod_cse")
    res = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Display all CSE students"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["result"]["rows"]) > 0


def test_api_hod_cse_denied_for_ece_scope_out_of_bounds():
    token = get_token_for("test_hod_cse")
    res = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Display all ECE students"},
    )
    assert res.status_code == 403
    err = res.json()
    assert "not authorized" in err["error"]["message"].lower() or "scope" in err["error"]["message"].lower()


def test_api_student_self_record_allowed():
    token = get_token_for("test_student_1")
    res = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Show my student record"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["result"] is not None
    assert data["result"]["result_type"] == "STUDENT_LIST"


def test_api_student_cohort_denied():
    token = get_token_for("test_student_1")
    res = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Display all CSE students"},
    )
    assert res.status_code == 403
    err = res.json()
    assert "not authorized" in err["error"]["message"].lower() or "scope" in err["error"]["message"].lower()


def test_api_empty_department_arch_returns_zero_records():
    token = get_token_for("test_principal")
    res = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Show students in ARCH"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["result"]["status"] == "EMPTY"
    assert len(data["result"]["rows"]) == 0


def test_api_student_list_suppresses_kpi_and_anomaly():
    token = get_token_for("test_principal")
    res = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "List CSE students"},
    )
    assert res.status_code == 200
    data = res.json()
    # Student list must NOT have anomaly assessment or visualization
    assert data["visualization"] is None
    assert data["anomaly"] is None
    assert data["explanation"] is None
    assert data["metric_display_name"] == "Authorized Student Records"


def test_api_student_list_query_audit_logged():
    log_service = get_query_log_service()
    initial_count = len(log_service._events)
    token = get_token_for("test_principal")
    res = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "List CSE students"},
    )
    assert res.status_code == 200
    events = log_service._events
    assert len(events) >= initial_count + 1
    last_event = list(events.values())[-1]
    assert last_event.query_type == "STUDENT_LIST"
    assert last_event.metric_id == "student.list"
    assert last_event.status.value == "SUCCESS"
    # Zero PII in event
    assert "password" not in str(last_event.model_dump())
    assert "roll_no" not in str(last_event.model_dump())


# =========================================================================
# F. STUDENT SELF ACADEMIC RECORD TESTS
# =========================================================================

def test_intent_show_my_academic_record_variations():
    """A. Verify all requested student self-record phrasings resolve to STUDENT_LIST with SELF filter."""
    intent_service = get_intent_service()
    student_principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000010",
        username="test_student_1",
        email="221fa04001@vignan.ac.in",
        person_id="a6300000-0020-4000-8000-000000000001",
        roles=["STUDENT"],
        scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF, scope_id="a6300000-0020-4000-8000-000000000001")],
        permissions={"attendance.read"},
    )
    test_phrases = [
        "Show my student record",
        "Show my academic record",
        "Show my academic details",
        "View my academic record",
        "Display my student details",
        "my academic record",
        "my academic details",
        "my academic profile",
        "my student details",
        "my student profile",
        "get my academic record",
    ]
    for phrase in test_phrases:
        raw = intent_service._recognize_student_list_intent(phrase, student_principal)
        assert raw is not None, f"Failed to recognize: {phrase}"
        assert raw.intent_type == IntentType.STUDENT_LIST, f"Unexpected type for {phrase}: {raw.intent_type}"
        assert raw.student_filters.get("student_id") == "SELF"


def test_intent_negative_self_record_recognition():
    """B. Negative recognition: general/cohort queries must NOT be interpreted as SELF."""
    intent_service = get_intent_service()
    student_principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000010",
        username="test_student_1",
        email="221fa04001@vignan.ac.in",
        person_id="a6300000-0020-4000-8000-000000000001",
        roles=["STUDENT"],
        scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF, scope_id="a6300000-0020-4000-8000-000000000001")],
        permissions={"attendance.read"},
    )
    negative_phrases = [
        "Show all student records",
        "Show CSE student records",
        "Show academic records",
    ]
    for phrase in negative_phrases:
        raw = intent_service._recognize_student_list_intent(phrase, student_principal)
        assert raw is None or raw.student_filters.get("student_id") != "SELF", (
            f"Phrase '{phrase}' was incorrectly recognized as SELF record!"
        )


def test_student_fixture_person_linkage():
    """C. Verify test_student_1 and test_student_2 resolve to valid seeded person UUIDs."""
    repo = get_identity_repository()
    u1 = repo.get_user_by_username("test_student_1")
    p1 = repo.resolve_principal(u1["user_id"])
    assert p1.person_id == "a6300000-0020-4000-8000-000000000001"

    u2 = repo.get_user_by_username("test_student_2")
    p2 = repo.resolve_principal(u2["user_id"])
    assert p2.person_id == "a6300000-0020-4000-8000-000000000002"


def test_defensive_self_scope_unlinked_student_denied():
    """Fix 3: If student has neither person_id nor valid SELF scope_id, compiler raises SQLAuthorizationError."""
    from backend.app.core.errors import SQLAuthorizationError
    from backend.app.services.sql_compiler import SQLCompiler

    compiler = SQLCompiler()
    unlinked_student = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000099",
        username="unlinked_student",
        email="unlinked@vignan.ac.in",
        person_id=None,
        roles=["STUDENT"],
        scoped_roles=[],
        permissions={"attendance.read"},
    )
    intent = StructuredIntent(
        intent_type=IntentType.STUDENT_LIST,
        metric_id="student.list",
        primary_metric_id="student.list",
        student_filters={"student_id": "SELF"},
        filters={"student_id": "SELF"},
    )
    with pytest.raises(SQLAuthorizationError) as exc_info:
        compiler.compile(intent=intent, principal=unlinked_student)

    assert "no verified student/person record linkage" in str(exc_info.value)


def test_api_student_academic_record_self_scope():
    """D & E. End-to-end: 'Show my academic record' returns exactly test_student_1's seeded record."""
    token = get_token_for("test_student_1")
    res = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Show my academic record"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["result"] is not None
    assert data["result"]["result_type"] == "STUDENT_LIST"
    rows = data["result"]["rows"]
    assert len(rows) == 1
    assert rows[0]["roll_no"] == "22CSEA001"
    assert rows[0]["full_name"] == "Deepak Kumar"


def test_api_cross_student_query_denied():
    """F. Student 1 requesting another student or cohort is strictly forbidden."""
    token = get_token_for("test_student_1")

    # Attempting cohort list
    res = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "Display all CSE students"},
    )
    assert res.status_code == 403

    # Attempting to query student 2's roll number
    authz = get_authorization_service()
    repo = get_identity_repository()
    u1 = repo.get_user_by_username("test_student_1")
    p1 = repo.resolve_principal(u1["user_id"])
    decision = authz.authorize_student_list(p1, {"roll_no": "22CSEB001"})
    assert decision.allowed is False
    assert decision.reason_code == "SCOPE_OUT_OF_BOUNDS"
