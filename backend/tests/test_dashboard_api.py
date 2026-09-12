"""Agent 63 - Phase 12: Role-Based Dashboard API Integration Tests

Verifies:
1. Unauthenticated requests to dashboard endpoints rejected (HTTP 401).
2. Authenticated Principal retrieves authorized catalog and dashboard (HTTP 200).
3. Authenticated HOD retrieves departmental dashboard and is denied Principal dashboard (HTTP 403).
4. Authenticated Student retrieves self dashboard and is denied executive dashboard (HTTP 403).
5. Quarantined Counsellor is denied institutional dashboards (HTTP 403).
6. Manual refresh endpoint forces execution (HTTP 200).
7. Schedule endpoints: CRUD flow (POST 201, GET 200, DELETE 200).
8. Sub-60 minute schedule intervals rejected (HTTP 400).
"""

from decimal import Decimal
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest

from backend.app.main import app

client = TestClient(app)


def get_auth_token(username: str = "test_principal") -> str:
    """Helper to acquire valid bearer token for a test identity."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "InstitutionalSecurePass123!"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


# 1. Unauthenticated requests rejected (401)
def test_unauthenticated_dashboard_requests_rejected():
    endpoints = [
        ("GET", "/api/v1/dashboard/catalog"),
        ("GET", "/api/v1/dashboard/principal_executive"),
        ("POST", "/api/v1/dashboard/principal_executive/refresh"),
        ("GET", "/api/v1/dashboard/schedules"),
        ("POST", "/api/v1/dashboard/schedules"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json={})
        assert res.status_code == 401, f"Expected 401 for unauthenticated {method} {path}"


# 2. Principal retrieves catalog and dashboard (200)
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_principal_dashboard_api(mock_db_execute):
    mock_db_execute.return_value = (
        ["value"],
        [{"value": Decimal("85.0")}],
        {"value": "numeric"},
        10.0,
    )

    token = get_auth_token("test_principal")
    headers = {"Authorization": f"Bearer {token}"}

    # Catalog
    res_cat = client.get("/api/v1/dashboard/catalog", headers=headers)
    assert res_cat.status_code == 200
    cat_data = res_cat.json()
    dash_ids = [d["dashboard_id"] for d in cat_data["dashboards"]]
    assert "principal_executive" in dash_ids

    # Dashboard Execution
    res_dash = client.get("/api/v1/dashboard/principal_executive", headers=headers)
    assert res_dash.status_code == 200
    dash_data = res_dash.json()
    assert dash_data["dashboard_id"] == "principal_executive"
    assert dash_data["role"] == "PRINCIPAL"
    assert len(dash_data["widgets"]) > 0


# 3. HOD accesses departmental dashboard; denied Principal dashboard (403)
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_hod_dashboard_api_boundaries(mock_db_execute):
    mock_db_execute.return_value = (
        ["pct"],
        [{"pct": Decimal("86.0")}],
        {"pct": "numeric"},
        8.0,
    )

    token = get_auth_token("test_hod_cse")
    headers = {"Authorization": f"Bearer {token}"}

    # HOD can access hod_department
    res_hod = client.get("/api/v1/dashboard/hod_department", headers=headers)
    assert res_hod.status_code == 200
    hod_data = res_hod.json()
    assert hod_data["dashboard_id"] == "hod_department"
    assert hod_data["scope"]["scope_type"] == "DEPARTMENT"

    # HOD denied principal_executive (403)
    res_prin = client.get("/api/v1/dashboard/principal_executive", headers=headers)
    assert res_prin.status_code == 403


# 4. Student accesses student dashboard; denied Principal dashboard (403)
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_student_dashboard_api_boundaries(mock_db_execute):
    mock_db_execute.return_value = (
        ["pct"],
        [{"pct": Decimal("90.0")}],
        {"pct": "numeric"},
        5.0,
    )

    token = get_auth_token("test_student_1")
    headers = {"Authorization": f"Bearer {token}"}

    # Student can access student_self
    res_stud = client.get("/api/v1/dashboard/student_self", headers=headers)
    assert res_stud.status_code == 200
    stud_data = res_stud.json()
    assert stud_data["dashboard_id"] == "student_self"
    assert stud_data["scope"]["scope_type"] == "SELF"

    # Student denied principal_executive (403)
    res_prin = client.get("/api/v1/dashboard/principal_executive", headers=headers)
    assert res_prin.status_code == 403


# 5. Quarantined Counsellor denied institutional dashboards (403)
def test_counsellor_denied_dashboard_api():
    token = get_auth_token("test_counsellor")
    headers = {"Authorization": f"Bearer {token}"}

    # Catalog is empty
    res_cat = client.get("/api/v1/dashboard/catalog", headers=headers)
    assert res_cat.status_code == 200
    assert len(res_cat.json()["dashboards"]) == 0

    # Requesting any dashboard returns 403
    res_prin = client.get("/api/v1/dashboard/principal_executive", headers=headers)
    assert res_prin.status_code == 403


# 6. Manual refresh endpoint executes cleanly (200)
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_manual_refresh_endpoint(mock_db_execute):
    mock_db_execute.return_value = (
        ["value"],
        [{"value": Decimal("85.0")}],
        {"value": "numeric"},
        10.0,
    )

    token = get_auth_token("test_principal")
    headers = {"Authorization": f"Bearer {token}"}

    res_refresh = client.post("/api/v1/dashboard/principal_executive/refresh", headers=headers)
    assert res_refresh.status_code == 200
    refresh_data = res_refresh.json()
    assert refresh_data["refresh_mode"] == "MANUAL"


# 7. Scheduled refresh endpoints CRUD flow
def test_scheduled_refresh_crud_flow():
    token = get_auth_token("test_principal")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create valid schedule (interval: 60)
    res_create = client.post(
        "/api/v1/dashboard/schedules",
        headers=headers,
        json={"dashboard_id": "principal_executive", "interval_minutes": 60},
    )
    assert res_create.status_code == 201
    created_data = res_create.json()
    schedule_id = created_data["schedule_id"]
    assert created_data["interval_minutes"] == 60

    # 2. List schedules
    res_list = client.get("/api/v1/dashboard/schedules", headers=headers)
    assert res_list.status_code == 200
    schedules = res_list.json()
    sched_ids = [s["schedule_id"] for s in schedules]
    assert schedule_id in sched_ids

    # 3. Cancel schedule
    res_cancel = client.delete(f"/api/v1/dashboard/schedules/{schedule_id}", headers=headers)
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"

    # 4. Verify no longer in active list
    res_list2 = client.get("/api/v1/dashboard/schedules", headers=headers)
    assert res_list2.status_code == 200
    sched_ids2 = [s["schedule_id"] for s in res_list2.json()]
    assert schedule_id not in sched_ids2


# 8. Sub-60 minute schedule rejected (400)
def test_sub_60_minute_schedule_rejected():
    token = get_auth_token("test_principal")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/dashboard/schedules",
        headers=headers,
        json={"dashboard_id": "principal_executive", "interval_minutes": 30},
    )
    assert res.status_code == 422 or res.status_code == 400
