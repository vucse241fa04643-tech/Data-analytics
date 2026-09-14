"""
Agent 63 - Principal Role Analytics Capabilities & Security Isolation Tests
Verifies that the PRINCIPAL role possesses the analytical depth to answer
operational leadership questions across the approved Phase 4 metric catalog while
strictly preserving role-isolation boundaries for non-principal roles and management.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

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
def principal_token() -> str:
    return get_auth_token("test_principal")


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


class TestPrincipalOperationalAnalyticsQueries:
    """Test suite executing the operational leadership queries for PRINCIPAL role."""

    # 1. Operational Attention Areas
    def test_01_operational_attention_attendance(self, principal_token):
        """Which departments need attention?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which departments need attention?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1
        assert any(r["department"] == "MECH" for r in rows)
        assert "institutional baseline" in data["explanation"]

    def test_02_operational_attention_pass_rate(self, principal_token):
        """Which departments have academic pass rate concerns?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which departments have academic pass rate concerns?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1
        assert any(r["department"] == "ECE" for r in rows)

    # 2. Baseline Comparisons
    def test_03_baseline_comparison_below(self, principal_token):
        """Which departments currently have attendance below the institutional level?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which departments currently have attendance below the institutional level?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1
        assert rows[0]["department"] == "MECH"
        assert rows[0]["metric_value"] < rows[0]["baseline_value"]
        assert rows[0]["difference"] < 0
        assert "institutional baseline" in data["explanation"]

    def test_04_baseline_comparison_pass_percentage(self, principal_token):
        """Which departments have pass percentage below institutional average?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which departments have pass percentage below institutional average?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1
        assert any(r["department"] == "ECE" for r in rows)
        assert any(r["difference"] < 0 for r in rows)

    # 3. Threshold Queries
    def test_05_threshold_attendance_below_75(self, principal_token):
        """Which departments have attendance below 75%?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which departments have attendance below 75%?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1
        assert any(r["department"] == "MECH" for r in rows)
        assert all(r["metric_value"] < 75.0 for r in rows)

    def test_06_threshold_pass_percentage_below_82(self, principal_token):
        """Which departments have course pass percentage below 82%?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which departments have course pass percentage below 82%?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1
        assert all(r["metric_value"] < 82.0 for r in rows)

    def test_07_threshold_course_pass_below_60(self, principal_token):
        """Which courses have pass rate below 60%?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which courses have pass rate below 60%?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data
        assert "explanation" in data

    # 4. Ranking & Extremes Queries
    def test_08_ranking_lowest_attendance(self, principal_token):
        """Which department has the lowest attendance?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which department has the lowest attendance?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert rows[0]["department"] == "MECH"
        assert "lowest current attendance" in data["explanation"]

    def test_09_ranking_highest_attendance(self, principal_token):
        """Which department has the highest attendance?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which department has the highest attendance?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert rows[0]["department"] == "EEE"

    def test_10_ranking_top_3_pass_percentage(self, principal_token):
        """What are the top 3 departments by pass percentage?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What are the top 3 departments by pass percentage?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert 1 <= len(rows) <= 3
        # Check order is descending
        if len(rows) > 1:
            assert rows[0]["metric_value"] >= rows[1]["metric_value"]

    def test_11_ranking_academic_year_lowest_attendance(self, principal_token):
        """Which academic year had the lowest attendance?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which academic year had the lowest attendance?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert rows[0]["academic_year"] == "2024-25"

    def test_12_ranking_academic_year_highest_pass_percentage(self, principal_token):
        """Which academic year had the highest pass percentage?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which academic year had the highest pass percentage?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert rows[0]["academic_year"] == "2023-24"

    # 5. Trend Queries
    def test_13_trend_attendance_academic_years(self, principal_token):
        """Show attendance trend over academic years."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Show attendance trend over academic years."},
            headers={"Authorization": f"Bearer {principal_token}"},
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

    def test_14_trend_pass_percentage_academic_years(self, principal_token):
        """Show pass percentage trend across academic years."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Show pass percentage trend across academic years."},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 2
        assert data["visualization"]["chart_type"] == "line"

    # 6. Change / Delta Queries
    def test_15_change_most_improved_attendance(self, principal_token):
        """Which department improved attendance the most?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which department improved attendance the most?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1
        assert rows[0]["department"] == "ECE"
        assert rows[0]["metric_value"] > 0

    def test_16_change_declined_attendance(self, principal_token):
        """Which department declined in attendance the most?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which department declined in attendance the most?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1
        assert rows[0]["metric_value"] < 0

    # 7. Multi-Department Comparisons
    def test_17_comparison_cse_vs_ece(self, principal_token):
        """Compare attendance between CSE and ECE."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Compare attendance between CSE and ECE."},
            headers={"Authorization": f"Bearer {principal_token}"},
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

    def test_18_comparison_cse_vs_ece_vs_mech(self, principal_token):
        """Compare attendance across CSE, ECE, and MECH."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Compare attendance across CSE, ECE, and MECH."},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 3
        depts = [r["department"] for r in rows]
        assert "CSE" in depts
        assert "ECE" in depts
        assert "MECH" in depts

    def test_19_comparison_all_departments_pass_percentage(self, principal_token):
        """Compare pass percentage across all departments."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Compare pass percentage across all departments."},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 3
        depts = [r["department"] for r in rows]
        assert "CSE" in depts
        assert "ECE" in depts
        assert "MECH" in depts

    # 8. Department Breakdowns
    def test_20_breakdown_student_strength(self, principal_token):
        """Show active student strength by department."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Show active student strength by department."},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 3
        assert any(r["department"] == "CSE" for r in rows)

    def test_21_breakdown_attendance_by_department(self, principal_token):
        """Show attendance breakdown by department."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Show attendance breakdown by department."},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 3

    # 9. Single Department Operational Queries
    def test_22_department_attendance_cse(self, principal_token):
        """What is the attendance of CSE?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the attendance of CSE?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 70.0

    def test_23_department_attendance_cse_specific_year(self, principal_token):
        """What was the CSE attendance for 2024-25?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What was the CSE attendance for 2024-25?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) == 78.01

    def test_24_department_pass_percentage_ece(self, principal_token):
        """What is the pass rate of ECE?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the pass rate of ECE?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) == 80.0

    # 10. Direct Institutional Metrics
    def test_25_direct_average_attendance(self, principal_token):
        """What is the average attendance percentage?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the average attendance percentage?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert 70.0 <= float(rows[0]["metric_value"]) <= 90.0

    def test_26_direct_course_pass_percentage(self, principal_token):
        """What is the course pass percentage?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the course pass percentage?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert 70.0 <= float(rows[0]["metric_value"]) <= 95.0

    def test_27_direct_students_passed(self, principal_token):
        """How many students passed?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "How many students passed?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 1000

    def test_28_direct_students_failed(self, principal_token):
        """How many students failed?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "How many students failed?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 100

    def test_29_direct_active_students(self, principal_token):
        """How many students are currently active?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "How many students are currently active?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 0

    def test_30_direct_placed_students(self, principal_token):
        """How many students were placed?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "How many students were placed?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 50

    def test_31_direct_average_ctc_formatting(self, principal_token):
        """What is the average CTC?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the average CTC?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 500000
        # Check human-readable CTC formatting in visualization / summary
        assert "lakh/year" in data["explanation"] or "₹" in data["explanation"]

    def test_32_direct_highest_ctc(self, principal_token):
        """What is the highest CTC?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the highest CTC?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 1000000

    def test_33_direct_placement_readiness(self, principal_token):
        """What is the average placement readiness score?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the average placement readiness score?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 0

    def test_34_direct_po_attainment(self, principal_token):
        """What is the PO attainment level?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the PO attainment level?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert 1.0 <= float(rows[0]["metric_value"]) <= 3.0

    def test_35_direct_latest_kpi_value(self, principal_token):
        """What is the latest KPI value?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "What is the latest KPI value?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 0

    def test_36_direct_course_offerings(self, principal_token):
        """How many active course offerings are there?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "How many active course offerings are there?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert float(rows[0]["metric_value"]) > 0


class TestSecurityIsolationAndRegressions:
    """Verifies that non-principal/non-management roles cannot execute out-of-scope analytics and Management is untouched."""

    def test_management_queries_continue_working(self, mgmt_token):
        """Management queries continue functioning exactly as before."""
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

    def test_student_cross_department_comparison_denied(self, student_token):
        """Student cannot compare departments."""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Compare attendance between CSE and ECE."},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code in (403, 422)


class TestPrincipalEdgeCasesAndFormattings:
    """Verifies edge cases, natural language variations, unit formatting, and safety limits."""

    def test_nl_variation_operational_investigation(self, principal_token):
        """Which areas require operational investigation?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which areas require operational investigation?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["result"]["rows"]) >= 1

    def test_nl_variation_low_attendance(self, principal_token):
        """Which departments have low attendance?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which departments have low attendance?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert any(r["department"] == "MECH" for r in data["result"]["rows"])

    def test_nl_variation_branches_falling_short(self, principal_token):
        """Which departments have attendance below 80%?"""
        resp = client.post(
            "/api/v1/agent/query",
            json={"prompt": "Which departments have attendance below 80%?"},
            headers={"Authorization": f"Bearer {principal_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(r["metric_value"] < 80.0 for r in data["result"]["rows"])

    def test_threshold_validation_out_of_bounds_rejected(self):
        """IntentValidator rejects percentage threshold values outside [0, 100]."""
        from backend.app.schemas.intent import StructuredIntent, IntentType
        from backend.app.services.intent_validator import IntentValidator

        validator = IntentValidator()
        invalid_intent = StructuredIntent(
            intent_type=IntentType.THRESHOLD_QUERY,
            metric_id="attendance.percentage",
            operator="<",
            threshold=150.0,
        )
        res = validator.validate_intent(invalid_intent)
        assert not res.is_valid
        assert res.message is not None
        assert "percentage" in res.message.lower()

    def test_threshold_validation_invalid_operator_rejected(self):
        """IntentValidator rejects unauthorized operators for threshold queries."""
        from backend.app.schemas.intent import StructuredIntent, IntentType
        from backend.app.services.intent_validator import IntentValidator

        validator = IntentValidator()
        invalid_intent = StructuredIntent(
            intent_type=IntentType.THRESHOLD_QUERY,
            metric_id="attendance.percentage",
            operator="LIKE",
            threshold=75.0,
        )
        res = validator.validate_intent(invalid_intent)
        assert not res.is_valid
        assert res.message is not None
        assert "operator" in res.message.lower()

    def test_visualization_insufficient_trend_data(self):
        """VisualizationService truthfulness when trend data has fewer than 2 data points."""
        from backend.app.schemas.query_result import QueryResult, QueryResultStatus, ExecutionMetadata
        from backend.app.schemas.intent import StructuredIntent, IntentType
        from backend.app.services.visualization_service import VisualizationService

        viz_service = VisualizationService()
        intent = StructuredIntent(
            intent_type=IntentType.TREND_QUERY,
            metric_id="attendance.percentage",
            dimensions=["academic_year"],
        )
        # Single row result
        single_row_res = QueryResult(
            status=QueryResultStatus.SUCCESS,
            result_type="TREND_QUERY",
            columns=["academic_year", "metric_value"],
            rows=[{"academic_year": "2025-26", "metric_value": 81.73}],
            row_count=1,
            metadata=ExecutionMetadata(
                execution_time_ms=10.0,
                row_count=1,
                columns=["academic_year", "metric_value"],
                data_types={"academic_year": "str", "metric_value": "float"},
                metric_id="attendance.percentage",
            ),
        )
        explanation = viz_service.generate_explanation(single_row_res, intent.model_dump())
        assert "Insufficient historical data" in explanation

    def test_clean_unit_formatting_students_and_offerings(self):
        """VisualizationService formats clean unit labels without raw identifiers."""
        from backend.app.services.visualization_service import _format_unit_symbol

        assert _format_unit_symbol("students_count") == " students"
        assert _format_unit_symbol("offerings_count") == " course offerings"
        assert _format_unit_symbol("level_scale") == ""
        assert _format_unit_symbol("kpi_unit") == ""
