"""
Agent 63 – Test Suite: Structured Intent Schema
Validates Pydantic schema validation, enum types, SQL filter injection guards,
and request/response envelope structures.
"""

import pytest
from pydantic import ValidationError

from backend.app.schemas.intent import (
    IntentRequest,
    IntentResponse,
    IntentType,
    IntentValidationStatus,
    StructuredIntent,
    TimeContext,
)


def test_valid_structured_intent():
    """Valid StructuredIntent instantiation passes validation."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        secondary_metric_ids=[],
        dimensions=["department"],
        filters={"department": "CSE"},
        time_context=TimeContext(academic_year="2024-2025"),
        reasoning_summary="CSE student attendance query",
    )
    assert intent.intent_type == IntentType.METRIC_QUERY
    assert intent.primary_metric_id == "attendance.percentage"
    assert intent.dimensions == ["department"]
    assert intent.filters == {"department": "CSE"}
    assert intent.time_context.academic_year == "2024-2025"


def test_sql_injection_rejected_in_filters():
    """Filters containing raw SQL keywords (SELECT, DROP, UNION, etc.) are strictly rejected."""
    malicious_filters = [
        {"department": "CSE'; DROP TABLE students; --"},
        {"query": "SELECT * FROM people.student"},
        {"condition": "1=1 UNION SELECT password FROM users"},
        {"clause": "WHERE 1=1"},
        {"action": "exec xp_cmdshell"},
    ]

    for f in malicious_filters:
        with pytest.raises(ValidationError) as exc_info:
            StructuredIntent(
                intent_type=IntentType.METRIC_QUERY,
                primary_metric_id="attendance.percentage",
                filters=f,
            )
        assert "Raw SQL clause or keyword" in str(exc_info.value)


def test_time_context_serialization():
    """TimeContext handles academic temporal parameters."""
    ctx = TimeContext(
        academic_year="2023-2024",
        term="SEM1",
        start_date="2023-08-01",
        end_date="2023-12-31",
    )
    assert ctx.academic_year == "2023-2024"
    assert ctx.term == "SEM1"


def test_intent_request_validation():
    """IntentRequest validates message length constraints (1 to 1000 chars)."""
    # Valid
    req = IntentRequest(message="What is the CSE attendance?")
    assert req.message == "What is the CSE attendance?"

    # Empty string fails
    with pytest.raises(ValidationError):
        IntentRequest(message="")

    # >1000 chars fails
    with pytest.raises(ValidationError):
        IntentRequest(message="a" * 1001)


def test_intent_response_envelope():
    """IntentResponse serializes properly with all statuses."""
    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
    )
    resp = IntentResponse(
        status=IntentValidationStatus.VALID,
        intent=intent,
        message="OK",
        request_id="test-req-123",
    )
    assert resp.status == IntentValidationStatus.VALID
    assert resp.intent.primary_metric_id == "attendance.percentage"
    assert resp.request_id == "test-req-123"
