"""
Agent 63 – Test Suite: Intent API Endpoints
Tests POST /api/v1/intent authentication, structured interpretation,
correlation ID preservation, error mapping (503/504), and authorization gating.
"""

from fastapi.testclient import TestClient
import pytest

from backend.app.core.errors import (
    GeminiConfigurationError,
    GeminiTimeoutError,
)
from backend.app.main import app
from backend.app.schemas.intent import (
    IntentType,
    IntentValidationStatus,
    StructuredIntent,
)
from backend.app.services.gemini_client import MockGeminiClient
from backend.app.services.intent_service import (
    IntentService,
    get_intent_service,
)

client = TestClient(app)


def get_auth_token(username: str = "test_principal") -> str:
    """Helper to acquire valid bearer token for a test identity."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "InstitutionalSecurePass123!"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


def test_post_intent_unauthenticated_returns_401():
    """Unauthenticated requests to /api/v1/intent are rejected with 401."""
    res = client.post(
        "/api/v1/intent",
        json={"message": "What is the attendance of CSE students?"},
    )
    assert res.status_code == 401


def test_post_intent_success_with_mock_gemini():
    """Authenticated request returns valid structured intent response."""
    mock_client = MockGeminiClient()
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="CSE attendance query",
    )
    mock_client.set_canned_intent(mock_intent)

    test_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_service

    try:
        token = get_auth_token("test_principal")
        headers = {"Authorization": f"Bearer {token}", "X-Request-ID": "test-req-corr-99"}

        res = client.post(
            "/api/v1/intent",
            headers=headers,
            json={"message": "What is the average attendance of CSE students?"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "VALID"
        assert data["intent"]["primary_metric_id"] == "attendance.percentage"
        assert data["intent"]["filters"]["department"] == "CSE"
        assert data["request_id"] == "test-req-corr-99"
        assert res.headers["x-request-id"] == "test-req-corr-99"
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


def test_post_intent_student_scope_rejected_in_response():
    """Student asking for department attendance is marked REJECTED in response."""
    mock_client = MockGeminiClient()
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="Department attendance lookup",
    )
    mock_client.set_canned_intent(mock_intent)

    test_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_service

    try:
        token = get_auth_token("test_student_1")
        headers = {"Authorization": f"Bearer {token}"}

        res = client.post(
            "/api/v1/intent",
            headers=headers,
            json={"message": "What is the average attendance of CSE students?"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "REJECTED"
        assert data["intent"] is None
        assert "restricted to self-scoped records" in data["message"]
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


def test_post_intent_gemini_timeout_returns_504():
    """Upstream Gemini timeout is mapped to clean HTTP 504 Gateway Timeout."""
    mock_client = MockGeminiClient()
    mock_client.set_timeout(True)

    test_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_service

    try:
        token = get_auth_token("test_principal")
        headers = {"Authorization": f"Bearer {token}"}

        res = client.post(
            "/api/v1/intent",
            headers=headers,
            json={"message": "What is the average attendance of CSE students?"},
        )
        assert res.status_code == 504
        data = res.json()
        assert data["error"]["code"] == "GEMINI_TIMEOUT"
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


def test_post_intent_gemini_unconfigured_returns_503():
    """Unconfigured Gemini client returns HTTP 503 Service Unavailable."""
    class UnconfiguredMock(MockGeminiClient):
        def generate_intent(self, user_message: str, system_instruction: str) -> StructuredIntent:
            raise GeminiConfigurationError("GEMINI_API_KEY is not configured")

    test_service = IntentService(gemini_client=UnconfiguredMock())
    app.dependency_overrides[get_intent_service] = lambda: test_service

    try:
        token = get_auth_token("test_principal")
        headers = {"Authorization": f"Bearer {token}"}

        res = client.post(
            "/api/v1/intent",
            headers=headers,
            json={"message": "What is the average attendance of CSE students?"},
        )
        assert res.status_code == 503
        data = res.json()
        assert data["error"]["code"] == "GEMINI_NOT_CONFIGURED"

    finally:
        app.dependency_overrides.pop(get_intent_service, None)


def test_post_intent_validation_length_error():
    """Empty message or message exceeding max length returns 422 Unprocessable Entity."""
    token = get_auth_token("test_principal")
    headers = {"Authorization": f"Bearer {token}"}

    # Empty
    res = client.post("/api/v1/intent", headers=headers, json={"message": ""})
    assert res.status_code == 422

    # Too long
    res = client.post("/api/v1/intent", headers=headers, json={"message": "x" * 1001})
    assert res.status_code == 422
