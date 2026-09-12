"""
Agent 63 – Test Suite: Intent Service
Tests system prompt compilation, end-to-end intent interpretation,
and server-side authorization enforcement across institutional roles and scopes.
"""

import pytest

from backend.app.schemas.intent import (
    IntentRequest,
    IntentType,
    IntentValidationStatus,
    StructuredIntent,
)
from backend.app.schemas.principal import (
    AuthenticatedPrincipal,
    ScopeType,
    ScopedRoleAssignment,
)
from backend.app.services.authorization import get_authorization_service
from backend.app.services.gemini_client import MockGeminiClient
from backend.app.services.intent_service import IntentService
from backend.app.services.intent_validator import IntentValidator
from backend.app.services.semantic_registry import get_semantic_registry_service


@pytest.fixture
def semantic_registry():
    return get_semantic_registry_service()


@pytest.fixture
def authz_service(semantic_registry):
    return get_authorization_service()


@pytest.fixture
def intent_service(semantic_registry, authz_service):
    mock_client = MockGeminiClient()
    validator = IntentValidator(semantic_registry=semantic_registry)
    return IntentService(
        gemini_client=mock_client,
        validator=validator,
        authorization_service=authz_service,
        semantic_registry=semantic_registry,
    )


@pytest.fixture
def principal_user():
    """Principal (Director/Head of Institution) with global analytics clearance."""
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)],
        permissions={
            "analytics.read",
            "attendance.read",
            "assessment.read",
            "outcomes.read",
            "placement.read",
            "academics.read",
            "quality.read",
        },
    )


@pytest.fixture
def hod_cse_user():
    """HOD CSE with departmental scope."""
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000004",
        username="test_hod_cse",
        email="hod.cse@vignan.ac.in",
        roles=["HOD"],
        scoped_roles=[
            ScopedRoleAssignment(
                role="HOD",
                scope_type=ScopeType.DEPARTMENT,
                scope_id="dept-cse-001",
            )
        ],
        permissions={"attendance.read", "assessment.read", "academics.read"},
    )


@pytest.fixture
def student_user():
    """Student with self-scope only."""
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000010",
        username="test_student_1",
        email="221fa04001@vignan.ac.in",
        person_id="student-uuid-s101",
        roles=["STUDENT"],
        scoped_roles=[
            ScopedRoleAssignment(
                role="STUDENT",
                scope_type=ScopeType.SELF,
                scope_id="student-uuid-s101",
            )
        ],
        permissions={"attendance.read", "assessment.read"},
    )


def test_build_system_prompt_catalog_grounding(intent_service):
    """System prompt contains only APPROVED metrics and valid dimensions."""
    prompt = intent_service.build_system_prompt()

    # Must contain approved metric
    assert "attendance.percentage" in prompt
    assert "academics.active_student_strength" in prompt


    # Must NOT contain review-required or deprecated metrics
    assert "attendance.students_below_threshold" not in prompt
    assert "placement.placement_rate" not in prompt

    # Must contain dimensions
    assert "department" in prompt
    assert "academic_year" in prompt

    # Must contain few-shot examples
    assert "FEW-SHOT EXAMPLES" in prompt
    assert "ZERO SQL" in prompt


def test_principal_query_cse_attendance_authorized(intent_service, principal_user):
    """Principal querying CSE attendance gets valid authorized intent."""
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="CSE attendance query",
    )
    intent_service._gemini_client.set_canned_intent(mock_intent)

    req = IntentRequest(message="What is the average attendance of CSE students?")
    resp = intent_service.interpret_intent(req, principal_user)

    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent is not None
    assert resp.intent.primary_metric_id == "attendance.percentage"
    assert resp.intent.filters["department"] == "CSE"


def test_student_querying_department_attendance_denied(intent_service, student_user):
    """Student attempting to query department-wide attendance is rejected."""
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="Attempted department attendance lookup",
    )
    intent_service._gemini_client.set_canned_intent(mock_intent)

    req = IntentRequest(message="Show me CSE attendance")
    resp = intent_service.interpret_intent(req, student_user)

    assert resp.status == IntentValidationStatus.REJECTED
    assert resp.intent is None
    assert "Student accounts are restricted to self-scoped records" in resp.message


def test_student_querying_own_attendance_authorized(intent_service, student_user):
    """Student querying self-scoped attendance is authorized."""
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        filters={},
        reasoning_summary="Self student attendance lookup",
    )
    intent_service._gemini_client.set_canned_intent(mock_intent)

    req = IntentRequest(message="What is my attendance?")
    resp = intent_service.interpret_intent(req, student_user)

    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent is not None


def test_hod_querying_other_department_denied(intent_service, hod_cse_user):
    """HOD CSE attempting to query ECE department is rejected for scope violation."""
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        filters={"department": "ECE"},
        reasoning_summary="Cross-department lookup",
    )
    intent_service._gemini_client.set_canned_intent(mock_intent)

    req = IntentRequest(message="What is ECE attendance?")
    resp = intent_service.interpret_intent(req, hod_cse_user)

    assert resp.status == IntentValidationStatus.REJECTED
    assert resp.intent is None
    assert "HOD scope violation" in resp.message


def test_out_of_scope_query(intent_service, principal_user):
    """Out of scope query returns OUT_OF_SCOPE status."""
    mock_intent = StructuredIntent(
        intent_type=IntentType.OUT_OF_SCOPE,
        primary_metric_id=None,
        reasoning_summary="General query about football",
    )
    intent_service._gemini_client.set_canned_intent(mock_intent)

    req = IntentRequest(message="Who won the match?")
    resp = intent_service.interpret_intent(req, principal_user)

    assert resp.status == IntentValidationStatus.OUT_OF_SCOPE
    assert resp.intent is not None


def test_clarification_needed_query(intent_service, principal_user):
    """Ambiguous query returns CLARIFICATION_REQUIRED status and questions."""
    mock_intent = StructuredIntent(
        intent_type=IntentType.CLARIFICATION_NEEDED,
        primary_metric_id=None,
        reasoning_summary="Vague metric request",
    )
    intent_service._gemini_client.set_canned_intent(mock_intent)

    req = IntentRequest(message="Show me stats")
    resp = intent_service.interpret_intent(req, principal_user)

    assert resp.status == IntentValidationStatus.CLARIFICATION_REQUIRED
    assert len(resp.clarification_questions) > 0
