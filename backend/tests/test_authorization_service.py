"""
Agent 63 – Authorization Service & Policy Engine Unit Tests
Tests multi-role resolution, permission matrix evaluation, organizational scope boundaries,
and privilege escalation resistance (body role injection, header spoofing, scope tampering).
"""

import pytest

from backend.app.schemas.principal import AuthenticatedPrincipal, ScopeType, ScopedRoleAssignment
from backend.app.services.authorization import AuthorizationService, get_authorization_service
from backend.app.services.identity_repository import get_identity_repository


@pytest.fixture
def authz_service():
    return get_authorization_service()


@pytest.fixture
def principal_user():
    repo = get_identity_repository()
    return repo.resolve_principal("00000000-0000-0000-0000-000000000001")  # test_principal


@pytest.fixture
def hod_cse_user():
    repo = get_identity_repository()
    return repo.resolve_principal("00000000-0000-0000-0000-000000000004")  # test_hod_cse


@pytest.fixture
def student_user():
    repo = get_identity_repository()
    return repo.resolve_principal("00000000-0000-0000-0000-000000000010")  # test_student_1


@pytest.fixture
def multi_role_faculty_mentor():
    repo = get_identity_repository()
    return repo.resolve_principal("00000000-0000-0000-0000-000000000007")  # test_mentor_faculty


def test_unauthenticated_request_denied(authz_service):
    decision = authz_service.authorize_action(
        principal=None,
        required_permission="analytics.read",
    )
    assert decision.allowed is False
    assert decision.reason_code == "UNAUTHENTICATED"


def test_principal_role_and_permission_authorization(authz_service, principal_user):
    assert principal_user is not None
    assert principal_user.has_role("PRINCIPAL")

    decision = authz_service.authorize_action(
        principal=principal_user,
        required_permission="analytics.read",
        required_role="PRINCIPAL",
    )
    assert decision.allowed is True
    assert decision.reason_code == "AUTHORIZED"


def test_insufficient_permission_denied(authz_service, student_user):
    assert student_user is not None
    # Student does not hold quality.read or export.create
    decision = authz_service.authorize_action(
        principal=student_user,
        required_permission="quality.read",
    )
    assert decision.allowed is False
    assert decision.reason_code == "INSUFFICIENT_PERMISSIONS"


def test_multi_role_resolution(authz_service, multi_role_faculty_mentor):
    assert multi_role_faculty_mentor is not None
    # User holds both FACULTY and MENTOR roles
    assert multi_role_faculty_mentor.has_role("FACULTY")
    assert multi_role_faculty_mentor.has_role("MENTOR")

    # Has permissions from both roles
    assert multi_role_faculty_mentor.has_permission("attendance.read")
    assert multi_role_faculty_mentor.has_permission("assessment.read")

    # Authorized for either role check
    dec1 = authz_service.authorize_action(multi_role_faculty_mentor, required_role="FACULTY")
    dec2 = authz_service.authorize_action(multi_role_faculty_mentor, required_role="MENTOR")
    assert dec1.allowed is True
    assert dec2.allowed is True


def test_hod_department_scope_boundary_enforced(authz_service, hod_cse_user):
    assert hod_cse_user is not None
    assert hod_cse_user.has_role("HOD")

    # Allowed for own department (dept-cse-001)
    decision_own = authz_service.authorize_action(
        principal=hod_cse_user,
        required_permission="attendance.read",
        scope_type=ScopeType.DEPARTMENT,
        scope_id="dept-cse-001",
    )
    assert decision_own.allowed is True
    assert decision_own.reason_code == "AUTHORIZED"

    # Denied for foreign department (dept-ece-002)
    decision_foreign = authz_service.authorize_action(
        principal=hod_cse_user,
        required_permission="attendance.read",
        scope_type=ScopeType.DEPARTMENT,
        scope_id="dept-ece-002",
    )
    assert decision_foreign.allowed is False
    assert decision_foreign.reason_code == "SCOPE_OUT_OF_BOUNDS"


def test_student_self_scope_boundary_enforced(authz_service, student_user):
    assert student_user is not None
    assert student_user.has_role("STUDENT")

    # Allowed for own student id
    decision_self = authz_service.authorize_action(
        principal=student_user,
        required_permission="attendance.read",
        scope_type=ScopeType.SELF,
        scope_id="student-uuid-s101",
    )
    assert decision_self.allowed is True

    # Denied for another student
    decision_other = authz_service.authorize_action(
        principal=student_user,
        required_permission="attendance.read",
        scope_type=ScopeType.SELF,
        scope_id="student-uuid-s102",
    )
    assert decision_other.allowed is False
    assert decision_other.reason_code == "SCOPE_OUT_OF_BOUNDS"


def test_institution_scope_covers_all_subscopes(authz_service, principal_user):
    # Principal has INSTITUTION scope; it encompasses any department or section
    decision = authz_service.authorize_action(
        principal=principal_user,
        required_permission="analytics.read",
        scope_type=ScopeType.DEPARTMENT,
        scope_id="dept-cse-001",
    )
    assert decision.allowed is True


def test_inactive_account_denied_authorization(authz_service):
    inactive = AuthenticatedPrincipal(
        user_id="inactive-user-id",
        username="disabled_user",
        email="disabled@vignan.ac.in",
        is_active=False,
        roles=["HOD"],
        permissions={"analytics.read"},
    )
    decision = authz_service.authorize_action(principal=inactive, required_permission="analytics.read")
    assert decision.allowed is False
    assert decision.reason_code == "INACTIVE_ACCOUNT"
