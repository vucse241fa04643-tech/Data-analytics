"""Agent 63 - Phase 11: Anomaly Detection API & Integration Tests

Verifies end-to-end endpoint delivery, RBAC security boundaries, and Phase 10 compatibility:
21. No authorization bypass (anomaly detection cannot grant permissions)
22. Confidential data remains strictly inaccessible (403 on confidential intent)
23. HOD scope remains unchanged (HOD CSE cannot query ECE anomaly)
24. Student scope remains unchanged (Student cannot query institutional anomaly)
25. Principal/IQAC/Dean scope remains authorized for institutional assessment
26. Phase 10 follow-up receives a fresh anomaly assessment
27. Previous anomaly is not reused across turns
28. Context reset removes previous analytical state
29. API response contract includes valid anomaly descriptor
30. Phase 9 visualization contract remains intact alongside anomaly assessment
"""

from decimal import Decimal
from unittest.mock import patch
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


# 21. No authorization bypass (unauthenticated requests rejected)
def test_unauthenticated_request_rejected_no_bypass():
    res = client.post(
        "/api/v1/agent/query",
        json={"prompt": "Show attendance anomalies for CSE"},
    )
    assert res.status_code == 401


# 22. Confidential data remains strictly inaccessible
def test_confidential_intent_rejected_without_anomaly_leak():
    mock_client = MockGeminiClient()
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="confidential.counselling_records",
        dimensions=[],
        filters={},
        reasoning_summary="Attempt to query confidential notes",
    )
    mock_client.set_canned_intent(mock_intent)
    test_intent_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_intent_service

    try:
        token = get_auth_token("test_principal")
        res = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"prompt": "Show confidential psychological logs"},
        )
        assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


# 23. HOD scope remains unchanged (HOD CSE cannot query ECE data or anomalies)
def test_hod_scope_enforcement_prevents_unauthorized_anomaly():
    mock_client = MockGeminiClient()
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "ECE"},  # ECE requested by CSE HOD
        reasoning_summary="ECE attendance query by CSE HOD",
    )
    mock_client.set_canned_intent(mock_intent)
    test_intent_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_intent_service

    try:
        token = get_auth_token("test_hod_cse")
        res = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"prompt": "Show attendance anomalies for ECE"},
        )
        assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


# 24. Student scope remains unchanged
def test_student_scope_enforcement_prevents_unauthorized_cross_student_anomaly():
    mock_client = MockGeminiClient()
    mock_intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="Departmental attendance query by student",
    )
    mock_client.set_canned_intent(mock_intent)
    test_intent_service = IntentService(gemini_client=mock_client)
    app.dependency_overrides[get_intent_service] = lambda: test_intent_service

    try:
        token = get_auth_token("test_student_1")
        res = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"prompt": "Show CSE attendance anomalies"},
        )
        # Student cannot query department-wide aggregated metric
        assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


# 25, 29, 30. Principal authorized query produces valid AnomalyAssessment and Phase 9 Visualization
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_agent_query_delivers_anomaly_and_visualization(mock_db_execute):
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

    # Mock database returning raw anomalous execution rows (68.0%)
    mock_db_execute.return_value = (
        ["adjusted_pct", "department_name"],
        [{"adjusted_pct": Decimal("68.0"), "department_name": "Computer Science"}],
        {"adjusted_pct": "numeric", "department_name": "text"},
        12.0,
    )

    app.dependency_overrides[get_intent_service] = lambda: test_intent_service

    try:
        token = get_auth_token("test_principal")
        with patch.object(settings.__class__, "is_database_configured", True):
            res = client.post(
                "/api/v1/agent/query",
                headers={"Authorization": f"Bearer {token}"},
                json={"prompt": "Show average attendance for CSE"},
            )
        assert res.status_code == 200
        data = res.json()

        # Phase 11 Anomaly Assessment Verification
        assert "anomaly" in data
        assert data["anomaly"] is not None
        assert data["anomaly"]["status"] == "ANOMALY_DETECTED"
        assert data["anomaly"]["detected"] is True
        assert data["anomaly"]["observed_value"] == 68.0
        assert data["anomaly"]["baseline_value"] == 75.0
        assert data["anomaly"]["baseline_type"] == "ANALYTICAL_HEURISTIC"
        assert data["anomaly"]["method"] == "CONFIGURED_THRESHOLD"
        assert "analytical heuristic and is not an official institutional policy" in data["anomaly"]["explanation"]
        assert "institutional requirement" not in data["anomaly"]["explanation"].lower()
        assert "The result does not establish the cause." in data["anomaly"]["explanation"]

        # Phase 9 Visualization Preservation Verification
        assert "visualization" in data
        assert data["visualization"] is not None
        assert data["visualization"]["chart_type"] == "kpi"
        assert data["explanation"] is not None
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


# 26, 27. Phase 10 multi-turn follow-up receives fresh anomaly; previous anomaly is not reused
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_phase_10_followup_receives_fresh_anomaly_assessment(mock_db_execute):
    mock_client = MockGeminiClient()
    # Turn 1 Intent: CSE (anomalous: 65.0%)
    intent_turn1 = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="attendance.percentage",
        dimensions=["department"],
        filters={"department": "CSE"},
        reasoning_summary="Turn 1: CSE",
    )
    mock_client.set_canned_intent(intent_turn1)
    test_intent_service = IntentService(gemini_client=mock_client)

    # Turn 1 result: 65% (anomalous)
    mock_db_execute.return_value = (
        ["adjusted_pct", "department_name"],
        [{"adjusted_pct": Decimal("65.0"), "department_name": "Computer Science"}],
        {"adjusted_pct": "numeric", "department_name": "text"},
        10.0,
    )

    app.dependency_overrides[get_intent_service] = lambda: test_intent_service

    try:
        token = get_auth_token("test_principal")
        with patch.object(settings.__class__, "is_database_configured", True):
            # Execute Turn 1
            res1 = client.post(
                "/api/v1/agent/query",
                headers={"Authorization": f"Bearer {token}"},
                json={"prompt": "Attendance for CSE"},
            )
            assert res1.status_code == 200
            data1 = res1.json()
            conv_id = data1["conversation_id"]
            assert data1["anomaly"]["status"] == "ANOMALY_DETECTED"
            assert data1["anomaly"]["observed_value"] == 65.0

            # Turn 2: "What about ECE?" (Normal attendance: 88.0%)
            intent_turn2 = StructuredIntent(
                intent_type=IntentType.METRIC_QUERY,
                primary_metric_id="attendance.percentage",
                dimensions=["department"],
                filters={"department": "ECE"},
                reasoning_summary="Turn 2: ECE follow-up",
            )
            mock_client.set_canned_intent(intent_turn2)
            # Turn 2 result: 88% (no anomaly)
            mock_db_execute.return_value = (
                ["adjusted_pct", "department_name"],
                [{"adjusted_pct": Decimal("88.0"), "department_name": "Electronics"}],
                {"adjusted_pct": "numeric", "department_name": "text"},
                10.0,
            )

            res2 = client.post(
                "/api/v1/agent/query",
                headers={"Authorization": f"Bearer {token}"},
                json={"prompt": "What about ECE?", "conversation_id": conv_id},
            )
            assert res2.status_code == 200
            data2 = res2.json()
            assert data2["conversation_id"] == conv_id
            assert data2["is_follow_up"] is True
            # Fresh anomaly assessment: NO_ANOMALY (not carried over from CSE)
            assert data2["anomaly"]["status"] == "NO_ANOMALY"
            assert data2["anomaly"]["detected"] is False
            assert data2["anomaly"]["observed_value"] == 88.0
            assert data2["anomaly"]["baseline_type"] == "ANALYTICAL_HEURISTIC"
    finally:
        app.dependency_overrides.pop(get_intent_service, None)


# 28. Context reset removes previous state cleanly
def test_conversation_reset_clears_state():
    token = get_auth_token("test_principal")
    res = client.delete(
        "/api/v1/agent/conversation/test-conv-12345",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "CLEARED"
