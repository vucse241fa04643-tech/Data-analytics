"""
Agent 63 - Phase 8: Agent Query API Integration Tests
Tests POST /api/v1/agent/query end-to-end pipeline:
1. Authentication gating (401)
2. Dry-run mode without database execution (200)
3. Fail-closed 503 response when database is unconfigured
4. Read-only execution and validated results when configured
5. Out-of-scope intent handling without SQL generation
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.schemas.intent import IntentType, StructuredIntent
from backend.app.services.gemini_client import MockGeminiClient
from backend.app.services.intent_service import IntentService, get_intent_service

client = TestClient(app)


def get_auth_token(username: str = "test_principal") -> str:
    """Helper to acquire valid bearer token for a test identity."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "InstitutionalSecurePass123!"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


def test_post_agent_query_unauthenticated_returns_401():
    """Unauthenticated requests to /api/v1/agent/query are rejected with 401."""
    res = client.post(
        "/api/v1/agent/query",
        json={"prompt": "What is the average attendance of CSE students?"},
    )
    assert res.status_code == 401


def test_post_agent_query_dry_run_unconfigured_db_succeeds():
    """In dry-run mode, SQL is compiled and validated without database execution."""
    mock_client = MockGeminiClient()
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="CSE attendance query",
    )
    mock_client.set_canned_intent(mock_intent)
    test_intent_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_intent_service

    try:
        token = get_auth_token("test_principal")
        headers = {"Authorization": f"Bearer {token}"}

        with patch.object(settings.__class__, "is_database_configured", False):
            res = client.post(
                "/api/v1/agent/query",
                headers=headers,
                json={"prompt": "What is the average attendance of CSE students?", "dry_run": True},
            )

        assert res.status_code == 200
        data = res.json()
        assert data["dry_run"] is True
        assert data["sql_artifact"] is not None
        assert data["result"] is None
        assert "SELECT" in data["sql_artifact"]["sql"]
        assert data["sql_artifact"]["read_only"] is True
        assert data["sql_artifact"]["validation_status"] == "VALID"
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


def test_post_agent_query_unconfigured_db_fails_closed_503():
    """When dry_run=False and database is unconfigured, endpoint returns HTTP 503."""
    mock_client = MockGeminiClient()
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="CSE attendance query",
    )
    mock_client.set_canned_intent(mock_intent)
    test_intent_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_intent_service

    try:
        token = get_auth_token("test_principal")
        headers = {"Authorization": f"Bearer {token}"}

        with patch.object(settings.__class__, "is_database_configured", False):
            res = client.post(
                "/api/v1/agent/query",
                headers=headers,
                json={"prompt": "What is the average attendance of CSE students?", "dry_run": False},
            )

        assert res.status_code == 503
        data = res.json()
        assert data["error"]["code"] == "DATABASE_NOT_CONFIGURED"
        assert "database connection is not configured" in data["error"]["message"].lower()
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_post_agent_query_successful_execution(mock_db_execute):
    """When configured, query compiles, executes read-only, and returns normalized results."""
    mock_client = MockGeminiClient()
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="CSE attendance query",
    )
    mock_client.set_canned_intent(mock_intent)
    test_intent_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_intent_service

    # Mock database returning raw execution rows
    mock_db_execute.return_value = (
        ["adjusted_pct", "department_name"],
        [{"adjusted_pct": Decimal("87.25"), "department_name": "Computer Science"}],
        {"adjusted_pct": "numeric", "department_name": "text"},
        18.5,
    )

    try:
        token = get_auth_token("test_principal")
        headers = {"Authorization": f"Bearer {token}"}

        with patch.object(settings.__class__, "is_database_configured", True):
            res = client.post(
                "/api/v1/agent/query",
                headers=headers,
                json={"prompt": "What is the average attendance of CSE students?", "dry_run": False},
            )

        assert res.status_code == 200
        data = res.json()
        assert data["dry_run"] is False
        assert data["sql_artifact"] is not None
        assert data["result"] is not None
        assert data["result"]["status"] == "SUCCESS"
        assert data["result"]["row_count"] == 1
        assert data["result"]["rows"][0]["adjusted_pct"] == 87.25
        assert data["result"]["columns"] == ["adjusted_pct", "department_name"]
        assert data["execution_metadata"]["execution_time_ms"] == 18.5
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


def test_post_agent_query_out_of_scope_intent():
    """Out-of-scope question returns guidance without compiling or executing SQL."""
    mock_client = MockGeminiClient()
    mock_intent = StructuredIntent(
        intent_type=IntentType.OUT_OF_SCOPE,
        reasoning_summary="Cafeteria menu is not in institutional analytics scope",
    )
    mock_client.set_canned_intent(mock_intent)
    test_intent_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_intent_service

    try:
        token = get_auth_token("test_principal")
        headers = {"Authorization": f"Bearer {token}"}

        res = client.post(
            "/api/v1/agent/query",
            headers=headers,
            json={"prompt": "What is for lunch in the college cafeteria today?"},
        )

        assert res.status_code == 200
        data = res.json()
        assert data["sql_artifact"] is None
        assert data["result"] is None
        assert "outside the scope of Agent 63" in data["message"]
    finally:
        app.dependency_overrides.pop(get_intent_service, None)
