"""
Agent 63 – Test Suite: Intent Robustness Regression Tests
Verifies robust handling of:
1. Normal successful Gemini responses (HTTP 200 + CORS).
2. Transient Gemini provider failures (HTTP 502 with sanitized message + CORS).
3. Malformed Gemini JSON responses (HTTP 502 controlled error + CORS).
4. Pydantic / Schema validation failures (HTTP 502 controlled error + CORS).
5. Metrics with null time_column in semantic catalog (AttributeError regression).
6. Immutable response schema generation across sequential requests.
7. Multiple sequential intent requests.
8. Enforced authentication (HTTP 401 for unauthenticated requests).
9. Enforced semantic authorization (scoped role gatekeeping).
"""

import json
from fastapi.testclient import TestClient
import pytest

from backend.app.core.errors import (
    GeminiError,
    GeminiTimeoutError,
)
from backend.app.main import app
from backend.app.schemas.intent import (
    IntentType,
    IntentValidationStatus,
    StructuredIntent,
)
from backend.app.services.gemini_client import (
    GeminiClient,
    MockGeminiClient,
    _build_developer_api_schema,
)
from backend.app.services.intent_service import (
    IntentService,
    get_intent_service,
)

client = TestClient(app)


def get_auth_token(username: str = "test_principal") -> str:
    """Helper to acquire a valid bearer token."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "InstitutionalSecurePass123!"},
    )
    assert res.status_code == 200, f"Login failed for {username}"
    return res.json()["access_token"]


def test_normal_successful_gemini_response():
    """1. Normal successful Gemini response produces HTTP 200 with CORS header."""
    mock_client = MockGeminiClient()
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="Valid attendance query for CSE department.",
    )
    mock_client.set_canned_intent(mock_intent)

    test_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_service

    try:
        token = get_auth_token("test_principal")
        headers = {
            "Authorization": f"Bearer {token}",
            "Origin": "http://localhost:5173",
        }

        res = client.post(
            "/api/v1/intent",
            headers=headers,
            json={"message": "What is the average attendance percentage for CSE students?"},
        )
        assert res.status_code == 200
        assert res.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
        data = res.json()
        assert data["status"] == "VALID"
        assert data["intent"]["primary_metric_id"] == "attendance.percentage"
        assert data["intent"]["filters"]["department"] == "CSE"
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


def test_gemini_transient_failure_controlled_502():
    """2. Gemini transient/client failure produces controlled HTTP 502 with safe notice and CORS."""
    mock_client = MockGeminiClient()
    mock_client.set_error("Agent 63's intent service is temporarily unavailable. Please try again.")

    test_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_service

    try:
        token = get_auth_token("test_principal")
        headers = {
            "Authorization": f"Bearer {token}",
            "Origin": "http://localhost:5173",
        }

        res = client.post(
            "/api/v1/intent",
            headers=headers,
            json={"message": "What is the average attendance percentage for CSE students?"},
        )
        assert res.status_code == 502
        assert res.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] == "GEMINI_ERROR"
        assert "temporarily unavailable" in data["error"]["message"].lower()
        # Ensure no raw API response or stack trace leaked
        assert "traceback" not in data["error"]["message"].lower()
        assert "generativelanguage" not in data["error"]["message"].lower()
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


def test_gemini_malformed_json_controlled_error():
    """3. Malformed Gemini non-JSON output produces controlled HTTP 502 error."""
    real_client = GeminiClient(api_key="mock_key")
    # Simulate generate_content returning non-JSON text
    class FakeResponse:
        text = "This is plain text, not a JSON object at all."

    class FakeModels:
        def generate_content(self, *args, **kwargs):
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    real_client._client = FakeClient()

    with pytest.raises(GeminiError) as exc_info:
        real_client.generate_intent("test question", "instruction")

    assert exc_info.value.status_code == 502
    assert "parse structured analytical intent" in exc_info.value.message


def test_gemini_pydantic_validation_failure_controlled_error():
    """4. Pydantic/schema validation failure on Gemini response produces controlled HTTP 502 error."""
    real_client = GeminiClient(api_key="mock_key")
    # Invalid intent_type that violates the enum
    class FakeResponse:
        text = '{"intent_type": "INVALID_NONEXISTENT_TYPE", "primary_metric_id": "test"}'

    class FakeModels:
        def generate_content(self, *args, **kwargs):
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    real_client._client = FakeClient()

    with pytest.raises(GeminiError) as exc_info:
        real_client.generate_intent("test question", "instruction")

    assert exc_info.value.status_code == 502
    assert "could not be validated against intent schema" in exc_info.value.message


def test_metrics_with_null_time_column_regression():
    """5. Metrics with time_column=null (academics.active_student_strength) do not raise AttributeError."""
    mock_client = MockGeminiClient()
    mock_intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="academics.active_student_strength",
        dimensions=["department"],
        filters={},
        reasoning_summary="Active student strength grouped by department.",
    )
    mock_client.set_canned_intent(mock_intent)

    test_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_service

    try:
        token = get_auth_token("test_principal")
        headers = {
            "Authorization": f"Bearer {token}",
            "Origin": "http://localhost:5173",
        }

        res = client.post(
            "/api/v1/intent",
            headers=headers,
            json={"message": "Show active student strength by department."},
        )
        assert res.status_code == 200
        assert res.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
        data = res.json()
        assert data["status"] == "VALID"
        assert data["intent"]["primary_metric_id"] == "academics.active_student_strength"
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


def test_schema_immutability_across_repeated_requests():
    """6. Repeated requests do not mutate StructuredIntent.model_json_schema()."""
    initial_schema_str = json.dumps(StructuredIntent.model_json_schema(), sort_keys=True)

    for _ in range(10):
        dev_schema = _build_developer_api_schema()
        # Verify developer api schema has stripped additionalProperties
        assert "additionalProperties" not in dev_schema
        current_schema_str = json.dumps(StructuredIntent.model_json_schema(), sort_keys=True)
        assert current_schema_str == initial_schema_str


def test_multiple_sequential_intent_requests():
    """7. Multiple sequential intent requests remain consistently successful."""
    mock_client = MockGeminiClient()
    test_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_service

    queries = [
        ("What is the average attendance percentage for CSE students?", "attendance.percentage", IntentType.METRIC_QUERY),
        ("Show active student strength by department.", "academics.active_student_strength", IntentType.BREAKDOWN_QUERY),
        ("Show the number of placed students by department.", "placement.placed_students_count", IntentType.METRIC_QUERY),
        ("What is the latest institutional KPI value?", "quality.kpi_latest_value", IntentType.METRIC_QUERY),
        ("Compare course pass percentage between CSE and ECE.", "assessment.course_pass_percentage", IntentType.COMPARISON_QUERY),
    ]

    try:
        token = get_auth_token("test_principal")
        headers = {
            "Authorization": f"Bearer {token}",
            "Origin": "http://localhost:5173",
        }

        for question, metric_id, intent_type in queries:
            mock_client.set_canned_intent(
                StructuredIntent(
                    intent_type=intent_type,
                    primary_metric_id=metric_id,
                    dimensions=["department"],
                    filters={"department": "CSE"} if metric_id != "academics.active_student_strength" else {},
                    reasoning_summary=f"Query for {metric_id}",
                )
            )
            res = client.post(
                "/api/v1/intent",
                headers=headers,
                json={"message": question},
            )
            assert res.status_code == 200, f"Failed for query '{question}': {res.text}"
            data = res.json()
            assert data["status"] == "VALID"
            assert data["intent"]["primary_metric_id"] == metric_id
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


def test_authentication_is_still_required():
    """8. Authentication is still required (HTTP 401 on unauthenticated intent requests)."""
    res = client.post(
        "/api/v1/intent",
        json={"message": "What is the average attendance percentage for CSE students?"},
    )
    assert res.status_code == 401
    assert "AUTHENTICATION_FAILED" in res.json()["error"]["code"]


def test_semantic_authorization_is_still_enforced():
    """9. Semantic authorization is still enforced for restricted roles (e.g. students)."""
    mock_client = MockGeminiClient()
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="Department level attendance lookup",
    )
    mock_client.set_canned_intent(mock_intent)

    test_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_service

    try:
        # Student requesting department-wide metric
        token = get_auth_token("test_student_1")
        headers = {
            "Authorization": f"Bearer {token}",
            "Origin": "http://localhost:5173",
        }

        res = client.post(
            "/api/v1/intent",
            headers=headers,
            json={"message": "What is the average attendance percentage for CSE students?"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "REJECTED"
        assert data["intent"] is None
        assert "restricted to self-scoped records" in data["message"]
    finally:
        app.dependency_overrides.pop(get_intent_service, None)
