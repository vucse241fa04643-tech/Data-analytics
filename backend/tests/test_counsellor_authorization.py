"""
Agent 63 – COUNSELLOR Role Authorization Security Tests
Verifies:
1. COUNSELLOR can list their assigned mentees (student list).
2. COUNSELLOR can access attendance metrics (mentee-scoped via SQL compiler).
3. COUNSELLOR can access assessment metrics (mentee-scoped via SQL compiler).
4. COUNSELLOR is denied all non-permitted domains (placement, quality, outcomes, academics).
5. COUNSELLOR is denied department-level or cohort student-list queries.
6. COUNSELLOR without person_id is denied (fail closed).
7. Inactive COUNSELLOR is denied.
8. SQL compiler injects the correct mentorship authorization predicate for student_list.
9. SQL compiler injects the correct mentorship authorization predicate for metric queries.
10. COUNSELLOR with department filter in student_list query is denied.
11. _recognize_counsellor_intent does not intercept non-COUNSELLOR principals.
"""
import pytest

from backend.app.schemas.principal import AuthenticatedPrincipal, ScopedRoleAssignment, ScopeType
from backend.app.schemas.intent import StructuredIntent, IntentType
from backend.app.services.authorization import AuthorizationService
from backend.app.services.identity_repository import reset_identity_repository
from backend.app.services.sql_compiler import get_sql_compiler
from backend.app.services.intent_service import IntentService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_repo():
    reset_identity_repository()
    yield
    reset_identity_repository()


FACULTY_PERSON_ID = "a6300000-0011-4000-8000-000000000001"  # Dr. Ramesh Kumar, faculty-001


def _make_counsellor(
    user_id: str = "test-counsellor-001",
    person_id: str = FACULTY_PERSON_ID,
    is_active: bool = True,
) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=user_id,
        username="test_counsellor",
        email="counsellor@vignan.ac.in",
        person_id=person_id,
        is_active=is_active,
        is_service_account=False,
        roles=["COUNSELLOR"],
        scoped_roles=[
            ScopedRoleAssignment(
                role="COUNSELLOR",
                scope_type=ScopeType.SELF,
                scope_id=person_id,
            )
        ],
        permissions={"counselling.read", "attendance.read", "assessment.read"},
    )


def _make_counsellor_no_person_id() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id="test-counsellor-nopid",
        username="test_counsellor_nopid",
        email="counsellor2@vignan.ac.in",
        person_id=None,
        is_active=True,
        is_service_account=False,
        roles=["COUNSELLOR"],
        scoped_roles=[ScopedRoleAssignment(role="COUNSELLOR", scope_type=ScopeType.SELF)],
        permissions={"counselling.read", "attendance.read", "assessment.read"},
    )


@pytest.fixture
def authz() -> AuthorizationService:
    return AuthorizationService()


@pytest.fixture
def compiler():
    return get_sql_compiler()


# ---------------------------------------------------------------------------
# 1. Student List – Authorization
# ---------------------------------------------------------------------------

class TestCounsellorStudentList:
    def test_counsellor_can_list_mentees(self, authz):
        counsellor = _make_counsellor()
        dec = authz.authorize_student_list(counsellor, student_filters={})
        assert dec.allowed is True
        assert dec.reason_code == "AUTHORIZED"

    def test_counsellor_denied_department_filter(self, authz):
        counsellor = _make_counsellor()
        dec = authz.authorize_student_list(counsellor, student_filters={"department": "CSE"})
        assert dec.allowed is False
        assert dec.reason_code == "SCOPE_OUT_OF_BOUNDS"

    def test_counsellor_denied_programme_filter(self, authz):
        counsellor = _make_counsellor()
        dec = authz.authorize_student_list(counsellor, student_filters={"programme": "B.Tech"})
        assert dec.allowed is False

    def test_counsellor_denied_batch_filter(self, authz):
        counsellor = _make_counsellor()
        dec = authz.authorize_student_list(counsellor, student_filters={"batch": "2022-2026"})
        assert dec.allowed is False

    def test_counsellor_without_person_id_denied(self, authz):
        counsellor = _make_counsellor_no_person_id()
        dec = authz.authorize_student_list(counsellor, student_filters={})
        assert dec.allowed is False
        assert dec.reason_code == "SCOPE_OUT_OF_BOUNDS"

    def test_inactive_counsellor_denied(self, authz):
        counsellor = _make_counsellor(is_active=False)
        dec = authz.authorize_student_list(counsellor, student_filters={})
        assert dec.allowed is False
        assert dec.reason_code == "INACTIVE_ACCOUNT"


# ---------------------------------------------------------------------------
# 2. Metric Authorization
# ---------------------------------------------------------------------------

class TestCounsellorMetricAuthorization:
    def test_counsellor_allowed_attendance(self, authz):
        counsellor = _make_counsellor()
        dec = authz.authorize_metric(counsellor, "attendance.percentage")
        assert dec.allowed is True
        assert dec.reason_code == "AUTHORIZED"

    def test_counsellor_allowed_assessment(self, authz):
        counsellor = _make_counsellor()
        dec = authz.authorize_metric(counsellor, "assessment.average_total_marks")
        assert dec.allowed is True

    def test_counsellor_denied_placement(self, authz):
        counsellor = _make_counsellor()
        dec = authz.authorize_metric(counsellor, "placement.placed_students_count")
        assert dec.allowed is False
        assert dec.reason_code == "INSUFFICIENT_PERMISSIONS"

    def test_counsellor_denied_outcomes(self, authz):
        counsellor = _make_counsellor()
        dec = authz.authorize_metric(counsellor, "outcomes.co_attainment_level")
        assert dec.allowed is False

    def test_counsellor_denied_quality(self, authz):
        counsellor = _make_counsellor()
        dec = authz.authorize_metric(counsellor, "quality.kpi_latest_value")
        assert dec.allowed is False

    def test_counsellor_denied_academics(self, authz):
        counsellor = _make_counsellor()
        dec = authz.authorize_metric(counsellor, "academics.active_student_strength")
        assert dec.allowed is False

    def test_counsellor_denied_department_scope(self, authz):
        counsellor = _make_counsellor()
        dec = authz.authorize_metric(
            counsellor,
            "attendance.percentage",
            requested_scope_type=ScopeType.DEPARTMENT,
            requested_scope_id="dept-cse-001",
        )
        assert dec.allowed is False
        assert dec.reason_code == "SCOPE_OUT_OF_BOUNDS"

    def test_counsellor_without_person_id_denied(self, authz):
        counsellor = _make_counsellor_no_person_id()
        dec = authz.authorize_metric(counsellor, "attendance.percentage")
        assert dec.allowed is False
        assert dec.reason_code == "SCOPE_OUT_OF_BOUNDS"

    def test_inactive_counsellor_metric_denied(self, authz):
        counsellor = _make_counsellor(is_active=False)
        dec = authz.authorize_metric(counsellor, "attendance.percentage")
        assert dec.allowed is False
        assert dec.reason_code == "INACTIVE_ACCOUNT"


# ---------------------------------------------------------------------------
EXPECTED_FACULTY_ID = "a6300000-0012-4000-8000-000000000001"  # people.faculty.faculty_id for DEV-FAC-001


# ---------------------------------------------------------------------------
# 2b. Centralized Identity Resolution Service Tests
# ---------------------------------------------------------------------------

class TestCounsellorIdentityResolution:
    def test_person_id_resolves_to_correct_faculty_id(self):
        """principal.person_id must resolve to people.faculty.faculty_id, not person_id."""
        from backend.app.services.identity_resolution import get_identity_resolution_service
        resolver = get_identity_resolution_service()
        counsellor = _make_counsellor()
        resolved = resolver.resolve_counsellor_faculty_id(counsellor)
        assert resolved == EXPECTED_FACULTY_ID
        assert resolved != FACULTY_PERSON_ID

    def test_missing_person_id_fails_closed(self):
        """Missing person_id must fail closed with SQLAuthorizationError."""
        from backend.app.core.errors import SQLAuthorizationError
        from backend.app.services.identity_resolution import get_identity_resolution_service
        resolver = get_identity_resolution_service()
        counsellor = _make_counsellor_no_person_id()
        with pytest.raises(SQLAuthorizationError):
            resolver.resolve_counsellor_faculty_id(counsellor)

    def test_wrong_faculty_mapping_fails_closed(self):
        """A person_id that does not exist in people.faculty must fail closed."""
        from backend.app.core.errors import SQLAuthorizationError
        from backend.app.services.identity_resolution import get_identity_resolution_service
        resolver = get_identity_resolution_service()
        counsellor = _make_counsellor(person_id="00000000-0000-0000-0000-999999999999")
        with pytest.raises(SQLAuthorizationError):
            resolver.resolve_counsellor_faculty_id(counsellor)

    def test_username_cannot_affect_identity_resolution(self):
        """Resolution is strictly grounded in person_id; changing username cannot alter faculty_id."""
        from backend.app.services.identity_resolution import get_identity_resolution_service
        resolver = get_identity_resolution_service()
        counsellor_alt_user = AuthenticatedPrincipal(
            user_id="alt-id",
            username="arbitrary_or_admin_username",
            email="alt@vignan.ac.in",
            person_id=FACULTY_PERSON_ID,
            is_active=True,
            is_service_account=False,
            roles=["COUNSELLOR"],
            scoped_roles=[ScopedRoleAssignment(role="COUNSELLOR", scope_type=ScopeType.SELF, scope_id=FACULTY_PERSON_ID)],
            permissions={"attendance.read"},
        )
        resolved = resolver.resolve_counsellor_faculty_id(counsellor_alt_user)
        assert resolved == EXPECTED_FACULTY_ID

    def test_multiple_faculty_rows_fails_closed(self):
        """If multiple faculty rows resolve for the same person_id, identity resolution must fail closed."""
        from unittest.mock import MagicMock
        from backend.app.core.errors import SQLAuthorizationError
        from backend.app.services.identity_resolution import IdentityResolutionService
        mock_db = MagicMock()
        mock_db.is_configured.return_value = True
        mock_db.execute_query.return_value = (
            ["faculty_id"],
            [{"faculty_id": "fac-1"}, {"faculty_id": "fac-2"}],
            0.1,
            2,
        )
        resolver = IdentityResolutionService(db_service=mock_db)
        counsellor = _make_counsellor()
        with pytest.raises(SQLAuthorizationError, match="Ambiguous faculty identity resolution"):
            resolver.resolve_counsellor_faculty_id(counsellor)


# ---------------------------------------------------------------------------
# 3. SQL Compiler – Authorization Predicate Injection
# ---------------------------------------------------------------------------

class TestCounsellorSQLPredicates:
    def test_student_list_injects_mentorship_predicate(self, compiler):
        """SQL compiler must inject mentorship subquery with resolved auth_counsellor_faculty_id."""
        counsellor = _make_counsellor()
        intent = StructuredIntent(
            intent_type=IntentType.STUDENT_LIST,
            metric_id="student.list",
            primary_metric_id="student.list",
            student_filters={},
            filters={},
            reasoning_summary="Counsellor lists mentees.",
        )
        artifact = compiler.compile(intent, counsellor)
        sql = artifact.sql.lower()
        params = artifact.parameters

        assert "studentlife.mentorship" in sql
        assert "auth_counsellor_faculty_id" in params
        assert params["auth_counsellor_faculty_id"] == EXPECTED_FACULTY_ID
        assert params["auth_counsellor_faculty_id"] != FACULTY_PERSON_ID
        assert "mentor_faculty_id = :auth_counsellor_faculty_id" in sql
        assert "is_current = true" in sql

    def test_attendance_metric_injects_mentorship_predicate(self, compiler):
        """SQL compiler must inject mentorship predicate with resolved faculty_id for metric query."""
        counsellor = _make_counsellor()
        intent = StructuredIntent(
            intent_type=IntentType.METRIC_QUERY,
            metric_id="attendance.percentage",
            primary_metric_id="attendance.percentage",
            filters={},
            reasoning_summary="Counsellor attendance query for mentees.",
        )
        artifact = compiler.compile(intent, counsellor)
        sql = artifact.sql.lower()
        params = artifact.parameters

        assert "studentlife.mentorship" in sql
        assert "auth_counsellor_faculty_id" in params
        assert params["auth_counsellor_faculty_id"] == EXPECTED_FACULTY_ID
        assert params["auth_counsellor_faculty_id"] != FACULTY_PERSON_ID
        # Must NOT scope by department
        assert "auth_department_code" not in params
        assert "auth_department_id" not in params

    def test_student_list_without_person_id_raises(self, compiler):
        """SQL compiler must raise SQLAuthorizationError for COUNSELLOR without person_id."""
        from backend.app.core.errors import SQLAuthorizationError
        counsellor = _make_counsellor_no_person_id()
        intent = StructuredIntent(
            intent_type=IntentType.STUDENT_LIST,
            metric_id="student.list",
            primary_metric_id="student.list",
            student_filters={},
            filters={},
            reasoning_summary="Counsellor without person_id.",
        )
        with pytest.raises(SQLAuthorizationError):
            compiler.compile(intent, counsellor)

    def test_attendance_without_person_id_raises(self, compiler):
        """SQL compiler must raise SQLAuthorizationError for metric query without person_id."""
        from backend.app.core.errors import SQLAuthorizationError
        counsellor = _make_counsellor_no_person_id()
        intent = StructuredIntent(
            intent_type=IntentType.METRIC_QUERY,
            metric_id="attendance.percentage",
            primary_metric_id="attendance.percentage",
            filters={},
            reasoning_summary="Counsellor without person_id.",
        )
        with pytest.raises(SQLAuthorizationError):
            compiler.compile(intent, counsellor)

    def test_payload_cannot_override_faculty_id(self, compiler):
        """Malicious payload parameters cannot override the server-side resolved faculty_id."""
        counsellor = _make_counsellor()
        intent = StructuredIntent(
            intent_type=IntentType.METRIC_QUERY,
            metric_id="attendance.percentage",
            primary_metric_id="attendance.percentage",
            filters={"faculty_id": "malicious-foreign-faculty-id", "auth_counsellor_faculty_id": "evil-id"},
            reasoning_summary="Tampered query.",
        )
        artifact = compiler.compile(intent, counsellor)
        params = artifact.parameters
        assert params["auth_counsellor_faculty_id"] == EXPECTED_FACULTY_ID
        assert params["auth_counsellor_faculty_id"] != "evil-id"

    def test_conversation_context_cannot_override_faculty_id(self, compiler):
        """Multi-turn context cannot override the server-side resolved faculty_id."""
        counsellor = _make_counsellor()
        intent = StructuredIntent(
            intent_type=IntentType.STUDENT_LIST,
            metric_id="student.list",
            primary_metric_id="student.list",
            student_filters={"mentor_faculty_id": "foreign-id"},
            filters={},
            reasoning_summary="Follow-up turn.",
        )
        artifact = compiler.compile(intent, counsellor)
        assert artifact.parameters["auth_counsellor_faculty_id"] == EXPECTED_FACULTY_ID

    def test_cross_department_access_remains_denied(self, authz):
        """Counsellor querying department scope is strictly denied."""
        counsellor = _make_counsellor()
        dec = authz.authorize_metric(
            counsellor, "attendance.percentage", requested_scope_type=ScopeType.DEPARTMENT
        )
        assert dec.allowed is False
        assert dec.reason_code == "SCOPE_OUT_OF_BOUNDS"


# ---------------------------------------------------------------------------
# 4. Intent Recognition – Deterministic Routing
# ---------------------------------------------------------------------------

class TestCounsellorIntentRecognition:
    def _svc(self) -> IntentService:
        return IntentService()

    def test_mentee_list_intent(self):
        counsellor = _make_counsellor()
        intent = self._svc()._recognize_counsellor_intent("show my mentees", counsellor)
        assert intent is not None
        assert intent.intent_type == IntentType.STUDENT_LIST
        assert intent.student_filters == {}

    def test_list_assigned_students_intent(self):
        counsellor = _make_counsellor()
        intent = self._svc()._recognize_counsellor_intent("list my assigned students", counsellor)
        assert intent is not None
        assert intent.intent_type == IntentType.STUDENT_LIST
        assert intent.student_filters == {}

    def test_mentee_attendance_intent(self):
        counsellor = _make_counsellor()
        intent = self._svc()._recognize_counsellor_intent(
            "show attendance for my mentees", counsellor
        )
        assert intent is not None
        assert intent.primary_metric_id == "attendance.percentage"
        assert intent.intent_type == IntentType.METRIC_QUERY

    def test_mentee_subject_wise_attendance_intent(self):
        counsellor = _make_counsellor()
        intent = self._svc()._recognize_counsellor_intent(
            "show subject-wise attendance for my mentees", counsellor
        )
        assert intent is not None
        assert intent.intent_type == IntentType.BREAKDOWN_QUERY
        assert "course" in (intent.dimensions or [])

    def test_mentee_academic_records_disabled(self):
        """Academic records capability is disabled pending student-level design (Requirement 10)."""
        counsellor = _make_counsellor()
        intent = self._svc()._recognize_counsellor_intent(
            "show academic records of my mentees", counsellor
        )
        assert intent is None

    def test_targeted_student_attendance_extracted(self):
        """Targeted individual student queries extract student identifier into filters."""
        counsellor = _make_counsellor()
        intent = self._svc()._recognize_counsellor_intent(
            "show attendance of 210101", counsellor
        )
        assert intent is not None
        assert intent.filters.get("roll_no") == "210101"

    def test_dept_scope_attempt_produces_rejectable_intent(self):
        """Department-scoped query produces a dept-filtered intent that authorization will deny."""
        counsellor = _make_counsellor()
        intent = self._svc()._recognize_counsellor_intent(
            "show attendance for all CSE students", counsellor
        )
        assert intent is not None
        filters = intent.filters or {}
        assert "department" in filters or "cse" in str(filters).lower()

    def test_non_counsellor_not_intercepted(self):
        """_recognize_counsellor_intent must return None for non-COUNSELLOR principals."""
        hod = AuthenticatedPrincipal(
            user_id="hod-01",
            username="test_hod_cse",
            email="hod@vignan.ac.in",
            person_id="hod-person-001",
            is_active=True,
            is_service_account=False,
            roles=["HOD"],
            scoped_roles=[
                ScopedRoleAssignment(
                    role="HOD", scope_type=ScopeType.DEPARTMENT, scope_id="dept-cse-001"
                )
            ],
            permissions={"analytics.read", "attendance.read"},
        )
        intent = self._svc()._recognize_counsellor_intent(
            "show attendance for my mentees", hod
        )
        assert intent is None

    def test_student_not_intercepted(self):
        """_recognize_counsellor_intent must return None for STUDENT principals."""
        student = AuthenticatedPrincipal(
            user_id="stu-01",
            username="test_student_1",
            email="student@vignan.ac.in",
            person_id="stu-person-01",
            is_active=True,
            is_service_account=False,
            roles=["STUDENT"],
            scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF)],
            permissions={"attendance.read"},
        )
        intent = self._svc()._recognize_counsellor_intent("show my mentees", student)
        assert intent is None


# ---------------------------------------------------------------------------
# 5. Unassigned Student Security & UX Semantics (Requirement 9)
# ---------------------------------------------------------------------------

class TestCounsellorUnassignedStudentSecurity:
    def test_unassigned_student_attendance_denied_scope_out_of_bounds(self, authz):
        """Querying attendance for an unassigned student must return SCOPE_OUT_OF_BOUNDS."""
        counsellor = _make_counsellor()
        # Student 210101 is not assigned to this counsellor
        dec = authz.authorize_metric(
            counsellor,
            "attendance.percentage",
            requested_scope_type=ScopeType.INSTITUTION,
            requested_scope_id="210101",
        )
        assert dec.allowed is False
        assert dec.reason_code == "SCOPE_OUT_OF_BOUNDS"
        assert "not authorized" in dec.message.lower()

    def test_unassigned_student_list_denied_scope_out_of_bounds(self, authz):
        """Student-list query targeting an unassigned student must return SCOPE_OUT_OF_BOUNDS."""
        counsellor = _make_counsellor()
        dec = authz.authorize_student_list(
            counsellor,
            student_filters={"roll_no": "210101"},
        )
        assert dec.allowed is False
        assert dec.reason_code == "SCOPE_OUT_OF_BOUNDS"
        assert "not authorized" in dec.message.lower()

    def test_does_not_reveal_student_existence(self, authz):
        """Identical rejection whether student exists in DB or is completely nonexistent."""
        counsellor = _make_counsellor()
        # 22CSEA010 exists in DB (people.student) but is not assigned to counsellor
        dec_exists = authz.authorize_student_list(counsellor, {"roll_no": "22CSEA010"})
        # FAKE999 does not exist anywhere
        dec_fake = authz.authorize_student_list(counsellor, {"roll_no": "FAKE999"})
        assert dec_exists.allowed is False
        assert dec_fake.allowed is False
        assert dec_exists.reason_code == dec_fake.reason_code == "SCOPE_OUT_OF_BOUNDS"
        assert dec_exists.message == dec_fake.message
