"""
Agent 63 – Test Suite: Intent Validator
Validates semantic catalog grounding, lifecycle status gatekeeping (APPROVED only),
dimension existence, metric-permitted dimensions, confidential schema exclusion,
strict semantic filter allowlisting, and SQL injection defenses.
"""

import pytest
from pydantic import ValidationError

from backend.app.schemas.intent import (
    IntentType,
    IntentValidationStatus,
    StructuredIntent,
)
from backend.app.services.intent_validator import IntentValidator
from backend.app.services.semantic_registry import get_semantic_registry_service


@pytest.fixture
def validator():
    return IntentValidator(semantic_registry=get_semantic_registry_service())


def test_validator_approves_valid_intent(validator):
    """An approved metric, valid dimension, and allowed filter passes validation."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
    )
    res = validator.validate_intent(intent)
    assert res.is_valid is True
    assert res.status == IntentValidationStatus.VALID
    assert res.validated_intent is not None


def test_validator_handles_out_of_scope(validator):
    """OUT_OF_SCOPE intent is recognized and marked as out of scope."""
    intent = StructuredIntent(
        intent_type=IntentType.OUT_OF_SCOPE,
        primary_metric_id=None,
        reasoning_summary="User asked about football results",
    )
    res = validator.validate_intent(intent)
    assert res.is_valid is False
    assert res.status == IntentValidationStatus.OUT_OF_SCOPE


def test_validator_handles_clarification_needed(validator):
    """CLARIFICATION_NEEDED intent generates clarification status."""
    intent = StructuredIntent(
        intent_type=IntentType.CLARIFICATION_NEEDED,
        primary_metric_id=None,
        reasoning_summary="Vague query",
    )
    res = validator.validate_intent(intent)
    assert res.is_valid is False
    assert res.status == IntentValidationStatus.CLARIFICATION_REQUIRED
    assert len(res.clarification_questions) > 0


def test_validator_rejects_missing_primary_metric(validator):
    """A METRIC_QUERY with null primary_metric_id is rejected."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id=None,
    )
    res = validator.validate_intent(intent)
    assert res.is_valid is False
    assert res.status == IntentValidationStatus.REJECTED
    assert res.error_code == "MISSING_PRIMARY_METRIC"


def test_validator_rejects_nonexistent_metric(validator):
    """Hallucinated/nonexistent metrics are strictly rejected."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="academics.invented_metric_xyz",
    )
    res = validator.validate_intent(intent)
    assert res.is_valid is False
    assert res.status == IntentValidationStatus.REJECTED
    assert res.error_code == "METRIC_NOT_FOUND"


def test_validator_rejects_review_required_metrics(validator):
    """Metrics with status REVIEW_REQUIRED (e.g. attendance.students_below_threshold) are rejected."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.students_below_threshold",
    )
    res = validator.validate_intent(intent)
    assert res.is_valid is False
    assert res.status == IntentValidationStatus.REJECTED
    assert res.error_code == "METRIC_NOT_APPROVED"


def test_validator_rejects_invalid_dimension(validator):
    """Invented dimension is rejected."""
    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["astrological_sign"],
    )
    res = validator.validate_intent(intent)
    assert res.is_valid is False
    assert res.status == IntentValidationStatus.REJECTED
    assert res.error_code == "INVALID_DIMENSION"


def test_validator_rejects_dimension_not_permitted_by_metric(validator):
    """Valid global dimension that is not permitted for the selected metric is rejected."""
    # 'faculty' is a valid dimension in the catalog, but attendance.percentage does not allow faculty grouping
    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["faculty"],
    )
    res = validator.validate_intent(intent)
    assert res.is_valid is False
    assert res.status == IntentValidationStatus.REJECTED
    assert res.error_code == "DIMENSION_NOT_PERMITTED"
    assert "not permitted for metric 'attendance.percentage'" in res.message


def test_validator_rejects_unknown_filter_key(validator):
    """Arbitrary/unknown filter key not in semantic catalog is rejected."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        filters={"random_database_column": "some_value"},
    )
    res = validator.validate_intent(intent)
    assert res.is_valid is False
    assert res.status == IntentValidationStatus.REJECTED
    assert res.error_code == "FILTER_NOT_PERMITTED"
    assert "random_database_column" in res.message


def test_validator_rejects_filter_not_permitted_by_metric(validator):
    """A dimension/filter exists in catalog but is not permitted for this specific metric."""
    # 'faculty' exists in catalog, but attendance.percentage does not permit faculty as a filter
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        filters={"faculty": "Dr. Sharma"},
    )
    res = validator.validate_intent(intent)
    assert res.is_valid is False
    assert res.status == IntentValidationStatus.REJECTED
    assert res.error_code == "FILTER_NOT_PERMITTED"
    assert "faculty" in res.message


def test_validator_accepts_valid_semantic_filters(validator):
    """Filters explicitly permitted by the metric's semantic definition are accepted."""
    # Test valid dimension filter
    intent_dept = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        filters={"department": "CSE"},
    )
    res_dept = validator.validate_intent(intent_dept)
    assert res_dept.is_valid is True
    assert res_dept.status == IntentValidationStatus.VALID

    # Test explicit allowed_filter attribute (e.g. batch_id, band)
    intent_batch = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        filters={"batch_id": "batch-2022-2026"},
    )
    res_batch = validator.validate_intent(intent_batch)
    assert res_batch.is_valid is True
    assert res_batch.status == IntentValidationStatus.VALID


def test_validator_rejects_database_table_name_in_filter(validator):
    """Raw database table or schema names in filter keys are rejected."""
    database_filter_keys = [
        "people.student",
        "attendance.attendance_event",
        "curriculum.course_version",
        "v_current_attendance",
        "tbl_users",
    ]
    for raw_key in database_filter_keys:
        intent = StructuredIntent(
            intent_type=IntentType.METRIC_QUERY,
            primary_metric_id="attendance.percentage",
            filters={raw_key: "123"},
        )
        res = validator.validate_intent(intent)
        assert res.is_valid is False
        assert res.status == IntentValidationStatus.REJECTED
        assert res.error_code == "FILTER_NOT_PERMITTED"


def test_validator_rejects_raw_sql_in_filters():
    """Pydantic model rejects raw SQL keywords in filters at parse time."""
    with pytest.raises(ValidationError) as exc:
        StructuredIntent(
            intent_type=IntentType.METRIC_QUERY,
            primary_metric_id="attendance.percentage",
            filters={"department": "CSE'; DROP TABLE students; --"},
        )
    assert "Raw SQL clause or keyword" in str(exc.value)


def test_every_referenced_test_metric_is_approved():
    """Verifies that all primary metrics referenced across Phase 6 tests are APPROVED in the registry."""
    registry = get_semantic_registry_service()
    metrics_to_check = [
        "attendance.percentage",
        "assessment.course_pass_percentage",
        "academics.active_student_strength",
    ]
    for m_id in metrics_to_check:
        metric = registry.get_metric(m_id)
        assert metric is not None, f"Metric '{m_id}' not found in registry"
        assert metric.get("status") == "APPROVED", f"Metric '{m_id}' is not APPROVED (status={metric.get('status')})"
