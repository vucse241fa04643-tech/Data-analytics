"""
Agent 63 - Management Analytics Capabilities & Security Isolation Tests
Verifies that the MANAGEMENT role possesses the analytical depth to answer
executive-level questions across the approved Phase 4 metric catalog while
strictly preserving role-isolation boundaries for non-management roles.
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.intent import IntentType, StructuredIntent
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopedRoleAssignment, ScopeType
from backend.app.services.sql_compiler import SQLCompiler

client = TestClient(app)


def get_auth_token(username: str) -> str:
    """Helper to acquire valid bearer token for a test identity."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "InstitutionalSecurePass123!"},
    )
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def mgmt_token() -> str:
    return get_auth_token("test_management")


@pytest.fixture(scope="module")
def hod_token() -> str:
    return get_auth_token("test_hod_cse")


@pytest.fixture(scope="module")
def counsellor_token() -> str:
    return get_auth_token("test_counsellor")


@pytest.fixture(scope="module")
def student_token() -> str:
    return get_auth_token("test_student_1")


class TestManagementAnalyticsQueries:
    """Test suite executing the 17 core executive queries for MANAGEMENT role."""

    def test_01_baseline_comparison(self, mgmt_token):
        """Which departments currently have attendance below the institutional level?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which departments currently have attendance below the institutional level?"},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1
        assert rows[0]["department"] == "MECH"
        assert rows[0]["metric_value"] < rows[0]["baseline_value"]
        assert rows[0]["difference"] < 0
        assert "institutional baseline" in data["explanation"]
        assert "MECH is below the institutional attendance level" in data["explanation"]

    def test_02_threshold_query(self, mgmt_token):
        """Which departments have attendance below 75%?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which departments have attendance below 75%?"},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1
        assert any(r["department"] == "MECH" for r in rows)
        assert all(r["metric_value"] < 75.0 for r in rows)

    def test_03_ranking_lowest(self, mgmt_token):
        """Which department has the lowest attendance?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which department has the lowest attendance?"},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert rows[0]["department"] == "MECH"
        assert "lowest current attendance" in data["explanation"]

    def test_04_trend_over_academic_years(self, mgmt_token):
        """Show attendance trend over academic years."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Show attendance trend over academic years."},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 2
        years = [r["academic_year"] for r in rows]
        assert "2023-24" in years
        assert "2024-25" in years
        assert "2025-26" in years
        assert data["visualization"]["chart_type"] == "line"

    def test_05_change_most_improved(self, mgmt_token):
        """Which department improved attendance the most?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which department improved attendance the most?"},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1
        assert rows[0]["department"] == "ECE"
        assert rows[0]["metric_value"] > 0

    def test_06_direct_average_attendance(self, mgmt_token):
        """What is the average attendance percentage?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the average attendance percentage?"},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert 70.0 <= float(rows[0]["metric_value"]) <= 90.0

    def test_07_direct_pass_percentage(self, mgmt_token):
        """What is the course pass percentage?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the course pass percentage?"},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert 70.0 <= float(rows[0]["metric_value"]) <= 95.0

    def test_08_direct_students_passed(self, mgmt_token):
        """How many students passed?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "How many students passed?"},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 1000

    def test_09_direct_students_failed(self, mgmt_token):
        """How many students failed?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "How many students failed?"},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 100

    def test_10_direct_average_ctc(self, mgmt_token):
        """What is the average CTC?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the average CTC?"},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 500000

    def test_11_direct_placed_students(self, mgmt_token):
        """How many students were placed?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "How many students were placed?"},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 50

    def test_12_direct_po_attainment(self, mgmt_token):
        """What is the PO attainment level?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the PO attainment level?"},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert 1.0 <= float(rows[0]["metric_value"]) <= 3.0

    def test_13_direct_latest_kpi(self, mgmt_token):
        """What is the latest KPI value?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the latest KPI value?"},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 0

    def test_14_comparison_across_departments(self, mgmt_token):
        """Compare pass percentage across departments."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Compare pass percentage across departments."},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 3
        depts = [r["department"] for r in rows]
        assert "CSE" in depts
        assert "ECE" in depts
        assert "MECH" in depts

    def test_15_comparison_cse_vs_ece(self, mgmt_token):
        """Compare attendance between CSE and ECE."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Compare attendance between CSE and ECE."},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 2
        depts = {r["department"]: r["metric_value"] for r in rows}
        assert "CSE" in depts
        assert "ECE" in depts
        assert depts["CSE"] == 82.02
        assert depts["ECE"] == 81.36
        assert "CSE vs ECE" in data["visualization"]["title"] or "CSE" in data["explanation"]

    def test_16_breakdown_student_strength(self, mgmt_token):
        """Show active student strength by department."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Show active student strength by department."},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 3
        assert any(r["department"] == "CSE" for r in rows)

    def test_17_filtered_metric_query(self, mgmt_token):
        """What is the CSE attendance for 2025-26?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the CSE attendance for 2025-26?"},
            headers={"Authorization": f"Bearer {mgmt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert rows[0]["metric_value"] == 85.02


class TestNonManagementSecurityIsolation:
    """Verifies that non-management roles are strictly denied out-of-scope institutional analytics."""

    def test_hod_cross_department_comparison_denied(self, hod_token):
        """HOD cannot perform cross-department comparison outside departmental boundary."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Compare attendance between CSE and ECE."},
            headers={"Authorization": f"Bearer {hod_token}"},
        )
        assert resp.status_code == 403
        assert resp.json().get("error", {}).get("code") == "SCOPE_OUT_OF_BOUNDS"

    def test_counsellor_institutional_baseline_denied(self, counsellor_token):
        """Counsellor cannot execute institutional baseline comparisons."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which departments currently have attendance below the institutional level?"},
            headers={"Authorization": f"Bearer {counsellor_token}"},
        )
        assert resp.status_code in (403, 422)

    def test_student_institutional_baseline_denied(self, student_token):
        """Student cannot execute institutional baseline comparisons."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which departments currently have attendance below the institutional level?"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code in (403, 422)
