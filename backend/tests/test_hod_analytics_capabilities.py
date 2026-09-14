"""Agent 63 - Secure Institutional Data Analytics Agent
HOD Analytics Capability & Security Isolation Test Suite

Verifies:
A. Direct Department Metrics (student strength, offerings, attendance, pass %, marks, attainment, placement, KPI)
B. Department Breakdowns (section, course, batch, year, academic year)
C. Department-Internal Rankings (highest, lowest, top N, bottom N)
D. Parameterized Threshold Questions (attendance < 75%, pass rate < 70%, pass rate > 90%)
E. Dynamic Baseline Comparisons (computed within authorized department, zero institutional baseline leakage)
F. Department-Internal Comparisons (section vs section, course vs course, academic year vs academic year)
G. Historical Trends (attendance, pass %, placement over academic years)
H. Deltas / Changes (year-over-year improvement / decline)
I. Authorized Student Record Access (in-department allowed, foreign student denied 403)
J. Comprehensive Security & Scope Isolation (cross-dept query 403, cross-dept comparison 403, institutional scope 403, context manipulation 403)
K. Multi-HOD Dynamic Verification (test_hod_cse and test_hod_ece use same dynamic pipeline)
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.authentication import get_authentication_service

client = TestClient(app)


def get_token(username: str) -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "InstitutionalSecurePass123!"},
    )
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def hod_cse_token() -> str:
    return get_token("test_hod_cse")


@pytest.fixture(scope="module")
def hod_ece_token() -> str:
    return get_token("test_hod_ece")


# =============================================================================
# A. DIRECT DEPARTMENT METRICS
# =============================================================================
class TestHODDirectMetrics:
    """Direct metrics automatically scoped to authorized HOD department."""

    def test_01_active_student_strength_cse(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "How many active students are in my department?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["rows"][0]["metric_value"] == 150
        assert data["scope"]["display"] == "HOD / CSE Department"

    def test_02_active_student_strength_ece(self, hod_ece_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_ece_token}"},
            json={"prompt": "How many active students are in my department?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["rows"][0]["metric_value"] == 120
        assert data["scope"]["display"] == "HOD / ECE Department"

    def test_03_active_offerings(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "How many course offerings are active?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["rows"][0]["metric_value"] >= 1

    def test_04_average_attendance_cse(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "What is our average attendance?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        val = float(data["result"]["rows"][0]["metric_value"])
        assert val == pytest.approx(82.02, 0.1)

    def test_05_average_attendance_ece(self, hod_ece_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_ece_token}"},
            json={"prompt": "What is our average attendance?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        val = float(data["result"]["rows"][0]["metric_value"])
        assert val == pytest.approx(81.36, 0.1)

    def test_06_raw_attendance(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "What is the average raw attendance?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["result"]["rows"]) == 1

    def test_07_course_pass_percentage_cse(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "What is our course pass percentage?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        val = float(data["result"]["rows"][0]["metric_value"])
        assert val == pytest.approx(85.0, 0.5)

    def test_08_average_total_marks(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "What is the average total marks?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["result"]["rows"]) == 1

    def test_09_students_passed_failed(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "How many students passed?"},
        )
        assert resp.status_code == 200
        resp_failed = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "How many students failed?"},
        )
        assert resp_failed.status_code == 200

    def test_10_co_and_po_attainment(self, hod_cse_token):
        resp_co = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "What is our CO attainment?"},
        )
        assert resp_co.status_code == 200
        resp_po = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "What is our PO attainment?"},
        )
        assert resp_po.status_code == 200

    def test_11_placement_metrics(self, hod_cse_token):
        resp_placed = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "How many students were placed?"},
        )
        assert resp_placed.status_code == 200
        resp_ctc = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "What is the average CTC?"},
        )
        assert resp_ctc.status_code == 200

    def test_12_kpi_query(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "What is the latest KPI value?"},
        )
        assert resp.status_code == 200


# =============================================================================
# B. DEPARTMENT BREAKDOWNS
# =============================================================================
class TestHODDepartmentBreakdowns:
    """Internal departmental breakdowns (sections, courses, batches, etc.)."""

    def test_01_attendance_by_section(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show attendance by section."},
        )
        assert resp.status_code == 200
        rows = resp.json()["result"]["rows"]
        assert len(rows) >= 2
        assert "section" in rows[0]

    def test_02_pass_percentage_by_course(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show pass percentage by course."},
        )
        assert resp.status_code == 200
        rows = resp.json()["result"]["rows"]
        assert len(rows) >= 1
        assert "course" in rows[0]

    def test_03_student_strength_by_batch(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show student strength by batch."},
        )
        assert resp.status_code == 200
        rows = resp.json()["result"]["rows"]
        assert len(rows) >= 1
        assert "batch" in rows[0]

    def test_04_co_attainment_by_course(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show CO attainment by course."},
        )
        assert resp.status_code == 200
        rows = resp.json()["result"]["rows"]
        assert len(rows) >= 1
        assert "course" in rows[0]

    def test_05_placement_by_batch(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show placement by batch."},
        )
        assert resp.status_code == 200
        rows = resp.json()["result"]["rows"]
        assert len(rows) >= 1


# =============================================================================
# C. RANKING / TOP / BOTTOM QUERIES
# =============================================================================
class TestHODRankings:
    """Department-internal ranking queries."""

    def test_01_lowest_pass_percentage_course(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Which course has the lowest pass percentage?"},
        )
        assert resp.status_code == 200
        rows = resp.json()["result"]["rows"]
        assert len(rows) == 1
        assert rows[0]["course"] == "CS304"
        assert float(rows[0]["metric_value"]) == pytest.approx(61.54, 0.1)

    def test_02_top_5_courses_by_pass_percentage(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Top 5 courses by pass percentage."},
        )
        assert resp.status_code == 200
        rows = resp.json()["result"]["rows"]
        assert 1 <= len(rows) <= 5
        # Verify descending order
        vals = [r["metric_value"] for r in rows]
        assert vals == sorted(vals, reverse=True)

    def test_03_section_highest_attendance(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Which section has the highest attendance?"},
        )
        assert resp.status_code == 200
        rows = resp.json()["result"]["rows"]
        assert len(rows) == 1
        assert "section" in rows[0]


# =============================================================================
# D. THRESHOLD QUESTIONS
# =============================================================================
class TestHODThresholds:
    """Department-internal threshold questions with parameters."""

    def test_01_attendance_below_75(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Which courses have attendance below 75%?"},
        )
        assert resp.status_code == 200
        # No courses below 75% in CSE seed
        rows = resp.json()["result"]["rows"]
        assert all(r["metric_value"] < 75.0 for r in rows)

    def test_02_pass_percentage_below_70(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Which courses have pass percentage below 70%?"},
        )
        assert resp.status_code == 200
        rows = resp.json()["result"]["rows"]
        assert len(rows) >= 1
        assert any(r["course"] == "CS304" for r in rows)
        assert all(r["metric_value"] < 70.0 for r in rows)

    def test_03_pass_percentage_above_90(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Which courses have pass percentage above 90%?"},
        )
        assert resp.status_code == 200
        rows = resp.json()["result"]["rows"]
        assert all(r["metric_value"] > 90.0 for r in rows)


# =============================================================================
# E. BASELINE COMPARISONS
# =============================================================================
class TestHODBaselineComparisons:
    """Baseline comparisons calculated dynamically from authorized department data."""

    def test_01_courses_below_department_average_cse(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Which courses are below the department average attendance?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1
        # Baseline must be CSE baseline (~82.02)
        b_val = float(rows[0]["baseline_value"])
        assert b_val == pytest.approx(82.02, 0.1)
        # All returned courses must be below baseline
        for r in rows:
            assert float(r["metric_value"]) < b_val
        # Explanation must state department baseline, not institutional
        assert "department baseline" in data["explanation"].lower()
        assert "institutional baseline" not in data["explanation"].lower()

    def test_02_courses_below_department_average_ece(self, hod_ece_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_ece_token}"},
            json={"prompt": "Which courses are below the department average attendance?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1
        # Baseline must be ECE baseline (~81.36)
        b_val = float(rows[0]["baseline_value"])
        assert b_val == pytest.approx(81.36, 0.1)
        for r in rows:
            assert float(r["metric_value"]) < b_val
        assert "department baseline" in data["explanation"].lower()


# =============================================================================
# F. INTERNAL COMPARISONS
# =============================================================================
class TestHODInternalComparisons:
    """Internal comparisons between entities in the authorized scope."""

    def test_01_compare_sections(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Compare Section A and Section B"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 2
        sections = [r["section"] for r in rows]
        assert "A" in sections and "B" in sections

    def test_02_compare_courses(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Compare CS301 and CS302"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 2
        courses = [r["course"] for r in rows]
        assert "CS301" in courses and "CS302" in courses

    def test_03_compare_academic_years(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Compare 2024-25 and 2025-26"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 2
        years = [r["academic_year"] for r in rows]
        assert "2024-25" in years and "2025-26" in years


# =============================================================================
# G. TREND ANALYSIS
# =============================================================================
class TestHODTrendAnalysis:
    """Historical trends within authorized department."""

    def test_01_attendance_trend(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show attendance trend"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 2
        assert "academic_year" in rows[0]

    def test_02_pass_percentage_trend(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show pass percentage trend."},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1

    def test_03_placement_trend(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show placement trend."},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) >= 1


# =============================================================================
# H. CHANGE / DELTA / IMPROVEMENT
# =============================================================================
class TestHODDeltas:
    """Department-internal delta and improvement questions."""

    def test_01_improved_attendance(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Which course improved attendance the most?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["status"] == "SUCCESS"


# =============================================================================
# I. STUDENT RECORD ACCESS
# =============================================================================
class TestHODStudentRecordAccess:
    """Authorized student record retrieval strictly scoped to HOD's department."""

    def test_01_show_all_students_in_my_department_cse(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show all students in my department."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["result_type"] == "STUDENT_LIST"
        rows = data["result"]["rows"]
        assert len(rows) > 0
        for r in rows:
            assert r["department_code"] == "CSE"

    def test_02_show_all_students_in_my_department_ece(self, hod_ece_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_ece_token}"},
            json={"prompt": "Show all students in my department."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["result_type"] == "STUDENT_LIST"
        rows = data["result"]["rows"]
        assert len(rows) > 0
        for r in rows:
            assert r["department_code"] == "ECE"

    def test_03_find_authorized_student_roll_no(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Find student 22CSEA001"},
        )
        assert resp.status_code == 200
        data = resp.json()
        rows = data["result"]["rows"]
        assert len(rows) == 1
        assert rows[0]["roll_no"] == "22CSEA001"
        assert rows[0]["department_code"] == "CSE"

    def test_04_find_unauthorized_foreign_student_roll_no_denied(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Find student 22ECEA001"},
        )
        assert resp.status_code == 403
        err = resp.json()["error"]
        assert err["code"] == "SCOPE_OUT_OF_BOUNDS"

    def test_05_students_in_section_a(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show students in Section A."},
        )
        assert resp.status_code == 200
        rows = resp.json()["result"]["rows"]
        assert len(rows) > 0
        for r in rows:
            assert r["department_code"] == "CSE"


# =============================================================================
# J. SECURITY & SCOPE ISOLATION
# =============================================================================
class TestHODSecurityIsolation:
    """Strict security boundaries preventing cross-department access or privilege escalation."""

    def test_01_cross_department_direct_query_blocked(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show ECE attendance"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "SCOPE_OUT_OF_BOUNDS"

    def test_02_cross_department_comparison_blocked(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Compare CSE and ECE"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "SCOPE_OUT_OF_BOUNDS"

    def test_03_compare_my_dept_with_other_blocked(self, hod_cse_token):
        resp = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Compare my department with ECE"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "SCOPE_OUT_OF_BOUNDS"

    def test_04_institution_wide_scope_queries_blocked(self, hod_cse_token):
        queries = [
            "Show all departments.",
            "Compare all departments.",
            "Which department has the lowest attendance?",
            "Which department has the highest pass percentage?",
            "Show all college students.",
            "Show institution-wide attendance.",
            "Show principal dashboard.",
            "Show management analytics.",
            "Show another HOD's data.",
            "Show another department's faculty.",
            "Show all students below 75% across college.",
        ]
        for q in queries:
            resp = client.post(
                "/api/v1/agent/query",
                headers={"Authorization": f"Bearer {hod_cse_token}"},
                json={"prompt": q},
            )
            assert resp.status_code == 403, f"Query '{q}' should be blocked 403 but got {resp.status_code}"
            assert resp.json()["error"]["code"] in ("SCOPE_OUT_OF_BOUNDS", "AUTHORIZATION_DENIED")

    def test_05_conversation_context_security(self, hod_cse_token):
        """Context turns must re-evaluate scope and block foreign department attempts."""
        # Turn 1: Valid department query
        r1 = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show attendance by subject"},
        )
        assert r1.status_code == 200
        conv_id = r1.json()["conversation_id"]

        # Turn 2: Follow-up staying in department
        r2 = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Which is the lowest?", "conversation_id": conv_id},
        )
        assert r2.status_code == 200

        # Turn 3: Attempting cross-department context tampering
        r3 = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Now show ECE instead", "conversation_id": conv_id},
        )
        assert r3.status_code == 403
        assert r3.json()["error"]["code"] == "SCOPE_OUT_OF_BOUNDS"


# =============================================================================
# K. MULTI-HOD DYNAMIC RESOLUTION
# =============================================================================
class TestMultiHODDynamicResolution:
    """Verifies that HOD CSE and HOD ECE dynamically resolve their distinct scopes."""

    def test_01_cse_and_ece_symmetric_isolation(self, hod_cse_token, hod_ece_token):
        # CSE HOD asking for CSE -> 200
        r_cse_ok = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show attendance for CSE"},
        )
        assert r_cse_ok.status_code == 200

        # CSE HOD asking for ECE -> 403
        r_cse_ece = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_cse_token}"},
            json={"prompt": "Show attendance for ECE"},
        )
        assert r_cse_ece.status_code == 403

        # ECE HOD asking for ECE -> 200
        r_ece_ok = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_ece_token}"},
            json={"prompt": "Show attendance for ECE"},
        )
        assert r_ece_ok.status_code == 200

        # ECE HOD asking for CSE -> 403
        r_ece_cse = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {hod_ece_token}"},
            json={"prompt": "Show attendance for CSE"},
        )
        assert r_ece_cse.status_code == 403
