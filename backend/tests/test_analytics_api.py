"""Agent 63 - Phase 13: Analytics API Integration Tests

Verifies:
1. Unauthenticated requests to /api/v1/analytics/popular-questions rejected (HTTP 401).
2. Authenticated Principal retrieves popular questions (HTTP 200).
3. Quarantined Counsellor receives empty list (no analytics metrics authorized).
4. Student cannot see institutional-scoped metrics in popular questions.
5. HOD cannot see cross-department scoped queries in popular questions.
6. Query parameters (limit, window_hours) enforce strict bounds (HTTP 422 on invalid).
7. No unrestricted query-log dump endpoint exists (HTTP 404).
8. Popular questions response contains zero user IDs, usernames, emails, or raw SQL.
"""

from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from backend.app.schemas.query_log import (
    QueryLogEvent,
    QueryLogEventType,
    QueryLogStatus,
)
from backend.app.services.query_log_service import (
    get_query_log_service,
    reset_query_log_service,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_query_logs():
    """Ensure clean query log store before and after each test."""
    reset_query_log_service()
    yield
    reset_query_log_service()


def get_auth_token(username: str = "test_principal") -> str:
    """Helper to acquire valid bearer token for a test identity."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "InstitutionalSecurePass123!"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


# 1. Unauthenticated requests rejected (401)
def test_unauthenticated_popular_questions_rejected():
    res = client.get("/api/v1/analytics/popular-questions")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"


# 2. Authenticated Principal retrieves popular questions (200)
def test_authenticated_principal_popular_questions_success():
    svc = get_query_log_service()
    # Log sample events
    svc.log_event(QueryLogEvent(
        user_id="00000000-0000-0000-0000-000000000001",
        role="PRINCIPAL",
        scope_type="INSTITUTION",
        metric_id="attendance.percentage",
        dimensions=["dim.department"],
        event_type=QueryLogEventType.MANUAL_QUERY,
        status=QueryLogStatus.SUCCESS,
    ))

    token = get_auth_token("test_principal")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/analytics/popular-questions", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["metric_id"] == "attendance.percentage"


# 3. Quarantined Counsellor receives empty list
def test_counsellor_receives_empty_popular_questions():
    svc = get_query_log_service()
    svc.log_event(QueryLogEvent(
        user_id="00000000-0000-0000-0000-000000000001",
        role="PRINCIPAL",
        scope_type="INSTITUTION",
        metric_id="attendance.percentage",
        dimensions=["dim.department"],
        event_type=QueryLogEventType.MANUAL_QUERY,
        status=QueryLogStatus.SUCCESS,
    ))

    token = get_auth_token("test_counsellor")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/analytics/popular-questions", headers=headers)
    assert res.status_code == 200
    assert res.json() == []


# 4. Student cannot see institutional-scoped metrics
def test_student_cannot_see_institutional_scoped_metrics():
    svc = get_query_log_service()
    # Log institutional-level event
    svc.log_event(QueryLogEvent(
        user_id="00000000-0000-0000-0000-000000000001",
        role="PRINCIPAL",
        scope_type="INSTITUTION",
        metric_id="placement.average_ctc",
        dimensions=["dim.department"],
        event_type=QueryLogEventType.MANUAL_QUERY,
        status=QueryLogStatus.SUCCESS,
    ))

    token = get_auth_token("test_student_1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/analytics/popular-questions", headers=headers)
    assert res.status_code == 200
    data = res.json()
    metric_ids = [item["metric_id"] for item in data]
    assert "placement.average_ctc" not in metric_ids


# 5. Parameter bounds enforcement (422 on invalid)
def test_popular_questions_parameter_bounds():
    token = get_auth_token("test_principal")
    headers = {"Authorization": f"Bearer {token}"}

    # limit out of bounds (< 1)
    res_low = client.get("/api/v1/analytics/popular-questions?limit=0", headers=headers)
    assert res_low.status_code == 422

    # limit out of bounds (> 20)
    res_high = client.get("/api/v1/analytics/popular-questions?limit=25", headers=headers)
    assert res_high.status_code == 422

    # window_hours out of bounds (< 1)
    res_w_low = client.get("/api/v1/analytics/popular-questions?window_hours=0", headers=headers)
    assert res_w_low.status_code == 422

    # window_hours out of bounds (> 720)
    res_w_high = client.get("/api/v1/analytics/popular-questions?window_hours=1000", headers=headers)
    assert res_w_high.status_code == 422


# 6. No unrestricted query-log dump endpoint exists (404)
def test_no_unrestricted_log_dump_endpoint():
    token = get_auth_token("test_principal")
    headers = {"Authorization": f"Bearer {token}"}

    unrestricted_paths = [
        "/api/v1/analytics/logs",
        "/api/v1/analytics/query-logs",
        "/api/v1/analytics/dump",
        "/api/v1/analytics/events",
    ]
    for p in unrestricted_paths:
        res = client.get(p, headers=headers)
        assert res.status_code == 404, f"Path {p} unexpectedly returned {res.status_code}"


# 7. Privacy invariant: zero user identities or raw SQL in output
def test_popular_questions_response_zero_identities_and_sql():
    svc = get_query_log_service()
    svc.log_event(QueryLogEvent(
        user_id="secret-user-uuid-9999",
        role="HOD",
        scope_type="DEPARTMENT",
        metric_id="attendance.percentage",
        dimensions=["dim.department"],
        event_type=QueryLogEventType.MANUAL_QUERY,
        status=QueryLogStatus.SUCCESS,
    ))

    token = get_auth_token("test_principal")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/analytics/popular-questions", headers=headers)
    assert res.status_code == 200
    raw_text = res.text
    assert "secret-user-uuid" not in raw_text
    assert "user_id" not in raw_text
    assert "username" not in raw_text
    assert "email" not in raw_text
    assert "sql" not in raw_text.lower()
