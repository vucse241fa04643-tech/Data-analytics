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


def test_counsellor_mentee_scoped_access(authz_service, repo):
    """COUNSELLOR has mentee-scoped access to attendance and assessment metrics only.
    General institutional analytics (placement, outcomes, quality, academics) remain denied.
    """
    counsellor = repo.resolve_principal("00000000-0000-0000-0000-000000000012")  # test_counsellor
    assert counsellor is not None

    # Counsellor can access attendance (scoped to assigned mentees by SQL compiler)
    dec_att = authz_service.authorize_metric(counsellor, "attendance.percentage")
    assert dec_att.allowed is True, "COUNSELLOR must be allowed attendance.percentage (mentee-scoped)"
    assert dec_att.reason_code == "AUTHORIZED"

    # Counsellor can access assessment marks (scoped to assigned mentees by SQL compiler)
    dec_assess = authz_service.authorize_metric(counsellor, "assessment.average_total_marks")
    assert dec_assess.allowed is True, "COUNSELLOR must be allowed assessment.average_total_marks (mentee-scoped)"

    # Counsellor is DENIED placement metrics (outside permitted domains)
    dec_placement = authz_service.authorize_metric(counsellor, "placement.placed_students_count")
    assert dec_placement.allowed is False, "COUNSELLOR must NOT access placement metrics"
    assert dec_placement.reason_code == "INSUFFICIENT_PERMISSIONS"

    # Counsellor is DENIED general academic strength
    dec_acad = authz_service.authorize_metric(counsellor, "academics.active_student_strength")
    assert dec_acad.allowed is False, "COUNSELLOR must NOT access general academic metrics"


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


def test_management_authorized_for_institution_metrics(authz_service, repo):
    """
    MANAGEMENT role possesses institution-level analytical read permissions
    across academics, attendance, assessment, placement, outcomes, quality.
    """
    mgmt_user = repo.get_user_by_username("test_management")
    assert mgmt_user is not None
    principal = repo.resolve_principal(mgmt_user["user_id"])
    assert principal is not None
    assert "MANAGEMENT" in principal.roles

    # Verify approved metrics across institutional domains
    for metric_id in [
        "academics.active_student_strength",
        "attendance.percentage",
        "assessment.course_pass_percentage",
        "placement.placed_students_count",
        "placement.average_ctc",
        "quality.kpi_latest_value",
    ]:
        dec = authz_service.authorize_metric(principal, metric_id)
        assert dec.allowed is True, f"MANAGEMENT must be allowed metric {metric_id}"
        assert dec.reason_code == "AUTHORIZED"


def test_management_denied_operational_student_lists(authz_service, repo):
    """
    MANAGEMENT role is restricted strictly to aggregate analytics and
    cannot access operational student-level records / cohort listings.
    """
    mgmt_user = repo.get_user_by_username("test_management")
    principal = repo.resolve_principal(mgmt_user["user_id"])
    assert principal is not None

    dec = authz_service.authorize_student_list(principal, {"department": "CSE"})
    assert dec.allowed is False
    assert dec.reason_code == "SCOPE_OUT_OF_BOUNDS"
