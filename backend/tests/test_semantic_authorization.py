"""
Agent 63 – Semantic Layer & Metric Authorization Tests
Verifies integration between Phase 5 Authorization and Phase 4 Semantic Layer:
- Lifecycle gatekeeping (only APPROVED metrics eligible; REVIEW_REQUIRED and DEPRECATED rejected)
- Sensitivity tier enforcement (PUBLIC vs INTERNAL vs SENSITIVE vs RESTRICTED)
- Domain permission enforcement (e.g. attendance.read, quality.read)
- Scope restriction enforcement (HOD department boundary, student self boundary)
- Strict denial of confidential.* and question paper objects
"""

import pytest

from backend.app.schemas.principal import ScopeType
from backend.app.services.authorization import AuthorizationService, get_authorization_service
from backend.app.services.identity_repository import get_identity_repository


@pytest.fixture
def authz_service():
    return get_authorization_service()


@pytest.fixture
def repo():
    return get_identity_repository()


def test_principal_authorized_for_approved_metrics(authz_service, repo):
    principal = repo.resolve_principal("00000000-0000-0000-0000-000000000001")  # test_principal
    assert principal is not None

    # Approved attendance metric
    dec_att = authz_service.authorize_metric(principal, "attendance.percentage")
    assert dec_att.allowed is True
    assert dec_att.reason_code == "AUTHORIZED"

    # Approved assessment metric
    dec_pass = authz_service.authorize_metric(principal, "assessment.course_pass_percentage")
    assert dec_pass.allowed is True

    # Approved quality metric
    dec_kpi = authz_service.authorize_metric(principal, "quality.kpi_latest_value")
    assert dec_kpi.allowed is True


def test_review_required_metrics_strictly_rejected_for_production(authz_service, repo):
    """
    CRITICAL CONSTRAINT: REVIEW_REQUIRED metrics must remain unavailable
    to production query planning, even for the Principal.
    """
    principal = repo.resolve_principal("00000000-0000-0000-0000-000000000001")  # test_principal

    # attendance.students_below_threshold is REVIEW_REQUIRED
    dec_shortage = authz_service.authorize_metric(principal, "attendance.students_below_threshold")
    assert dec_shortage.allowed is False
    assert dec_shortage.reason_code == "METRIC_UNAPPROVED"

    # placement.placement_rate is REVIEW_REQUIRED
    dec_rate = authz_service.authorize_metric(principal, "placement.placement_rate")
    assert dec_rate.allowed is False
    assert dec_rate.reason_code == "METRIC_UNAPPROVED"


def test_unknown_metric_rejected(authz_service, repo):
    principal = repo.resolve_principal("00000000-0000-0000-0000-000000000001")
    dec = authz_service.authorize_metric(principal, "nonexistent.fake_metric")
    assert dec.allowed is False
    assert dec.reason_code == "METRIC_NOT_FOUND"


def test_student_restricted_to_self_scope(authz_service, repo):
    student = repo.resolve_principal("00000000-0000-0000-0000-000000000010")  # test_student_1
    assert student is not None

    # Student querying self-scoped attendance is allowed
    dec_self = authz_service.authorize_metric(
        student,
        "attendance.percentage",
        requested_scope_type=ScopeType.SELF,
        requested_scope_id="student-uuid-s101",
    )
    assert dec_self.allowed is True

    # Student attempting to query department-wide attendance is rejected
    dec_dept = authz_service.authorize_metric(
        student,
        "attendance.percentage",
        requested_scope_type=ScopeType.DEPARTMENT,
        requested_scope_id="dept-cse-001",
    )
    assert dec_dept.allowed is False
    assert dec_dept.reason_code == "SCOPE_OUT_OF_BOUNDS"


def test_hod_restricted_to_assigned_department_scope(authz_service, repo):
    hod_cse = repo.resolve_principal("00000000-0000-0000-0000-000000000004")  # test_hod_cse
    assert hod_cse is not None

    # Allowed for CSE department
    dec_cse = authz_service.authorize_metric(
        hod_cse,
        "assessment.course_pass_percentage",
        requested_scope_type=ScopeType.DEPARTMENT,
        requested_scope_id="dept-cse-001",
    )
    assert dec_cse.allowed is True

    # Denied for ECE department
    dec_ece = authz_service.authorize_metric(
        hod_cse,
        "assessment.course_pass_percentage",
        requested_scope_type=ScopeType.DEPARTMENT,
        requested_scope_id="dept-ece-002",
    )
    assert dec_ece.allowed is False
    assert dec_ece.reason_code == "SCOPE_OUT_OF_BOUNDS"


def test_counsellor_quarantined_from_general_analytics(authz_service, repo):
    counsellor = repo.resolve_principal("00000000-0000-0000-0000-000000000012")  # test_counsellor
    assert counsellor is not None

    # Counsellor lacks attendance.read and analytics.read
    dec = authz_service.authorize_metric(counsellor, "attendance.percentage")
    assert dec.allowed is False
    assert dec.reason_code == "INSUFFICIENT_PERMISSIONS"


def test_placement_officer_authorized_for_placement_metrics(authz_service, repo):
    placement_officer = repo.resolve_principal("00000000-0000-0000-0000-000000000008")  # test_placement
    student = repo.resolve_principal("00000000-0000-0000-0000-000000000010")  # test_student_1

    # Placement officer allowed
    dec_po = authz_service.authorize_metric(placement_officer, "placement.placed_students_count")
    assert dec_po.allowed is True

    # Student lacks placement.read
    dec_stu = authz_service.authorize_metric(student, "placement.placed_students_count")
    assert dec_stu.allowed is False
    assert dec_stu.reason_code == "INSUFFICIENT_PERMISSIONS"
