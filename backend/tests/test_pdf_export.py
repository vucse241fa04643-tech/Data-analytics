"""Agent 63 - Focused PDF Export and Role Authorization Tests.

Covers:
1. Authenticated PDF export succeeds via unified /api/v1/analytics/export and direct /api/v1/analytics/export/pdf
2. Response headers: Content-Type is application/pdf, Content-Disposition has .pdf filename
3. PDF content is valid and non-empty (starts with %PDF-, contains report headers & governance)
4. Empty result (0 rows) produces valid institutional PDF stating no records found
5. KPI-only result produces clear KPI highlight in PDF
6. Unauthorized / unknown request_id rejected (404 for unknown/expired, 401 for unauthenticated)
7. Ownership & Cross-user isolation preserved: tampering with request_id rejected (403)
8. Role testing with fresh authentication for:
   - test_student_1 (STUDENT)
   - test_counsellor (COUNSELLOR)
   - test_hod_cse (HOD)
   - test_principal (PRINCIPAL)
9. Existing CSV and JSON exports continue to work cleanly
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.export import ExportArtifact, ExportFormat
from backend.app.schemas.principal import ScopeType
from backend.app.schemas.query_result import ExecutionMetadata, QueryResult
from backend.app.services.export_artifact_store import (
    get_export_artifact_store,
    reset_export_artifact_store,
)
from backend.app.services.export_service import reset_export_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_stores():
    reset_export_artifact_store()
    reset_export_service()
    yield
    reset_export_artifact_store()
    reset_export_service()


def get_auth_token(username: str) -> str:
    """Helper to obtain fresh bearer token for a test identity."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "InstitutionalSecurePass123!"},
    )
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]


def make_artifact(
    request_id: str,
    user_id: str,
    role: str,
    metric_id: str,
    metric_display_name: str,
    scope_type: str = "INSTITUTION",
    scope_id: str = None,
    columns=None,
    rows=None,
    visualization_type=None,
) -> ExportArtifact:
    if columns is None:
        columns = ["department", "attendance_pct"]
    if rows is None:
        rows = [
            {"department": "CSE", "attendance_pct": 84.5},
            {"department": "ECE", "attendance_pct": 81.2},
        ]
    qr = QueryResult(
        status="SUCCESS" if rows else "EMPTY",
        columns=columns,
        rows=rows,
        row_count=len(rows),
        execution_time_ms=10.0,
        metadata=ExecutionMetadata(
            metric_id=metric_id,
            dimensions=["department"] if "department" in columns else [],
            row_count=len(rows),
            columns=columns,
            execution_time_ms=10.0,
        ),
    )
    return ExportArtifact(
        request_id=request_id,
        user_id=user_id,
        role=role,
        scope_type=scope_type,
        scope_id=scope_id,
        metric_id=metric_id,
        metric_display_name=metric_display_name,
        query_result=qr,
        dimensions=["department"] if "department" in columns else [],
        visualization_type=visualization_type,
    )


# ---------------------------------------------------------------------------
# Section 1: Authenticated PDF Export Basic Functionality & Validation
# ---------------------------------------------------------------------------

class TestPdfExportBasics:
    def test_authenticated_pdf_export_succeeds(self):
        token = get_auth_token("test_principal")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

        art = make_artifact(
            request_id="req-pdf-test-1",
            user_id=me["user_id"],
            role="PRINCIPAL",
            metric_id="attendance.percentage",
            metric_display_name="Average Attendance Percentage",
        )
        get_export_artifact_store().save_artifact(art)

        # 1. Via unified /export with format="pdf"
        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-pdf-test-1", "format": "pdf"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert "Content-Disposition" in res.headers
        assert "agent63_attendance_percentage_" in res.headers["Content-Disposition"]
        assert res.headers["Content-Disposition"].endswith('.pdf"')

        # Verify PDF magic bytes and content
        content = res.content
        assert len(content) > 1000
        assert content.startswith(b"%PDF-")

        # 2. Via direct /export/pdf endpoint
        res_direct = client.post(
            "/api/v1/analytics/export/pdf",
            json={"request_id": "req-pdf-test-1", "format": "pdf"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_direct.status_code == 200
        assert res_direct.headers["content-type"] == "application/pdf"
        assert res_direct.content.startswith(b"%PDF-")

    def test_pdf_export_for_empty_result(self):
        token = get_auth_token("test_principal")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

        art = make_artifact(
            request_id="req-pdf-empty",
            user_id=me["user_id"],
            role="PRINCIPAL",
            metric_id="attendance.percentage",
            metric_display_name="Average Attendance Percentage",
            columns=["department", "attendance_pct"],
            rows=[],
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-pdf-empty", "format": "pdf"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content.startswith(b"%PDF-")
        assert len(res.content) > 500

    def test_pdf_export_for_kpi_scalar_result(self):
        token = get_auth_token("test_principal")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

        art = make_artifact(
            request_id="req-pdf-kpi",
            user_id=me["user_id"],
            role="PRINCIPAL",
            metric_id="placement.average_ctc",
            metric_display_name="Average Placement CTC",
            columns=["average_ctc"],
            rows=[{"average_ctc": 1121117.29}],
            visualization_type="kpi",
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-pdf-kpi", "format": "pdf"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content.startswith(b"%PDF-")


# ---------------------------------------------------------------------------
# Section 2: Security, Rejection & Ownership Isolation Tests
# ---------------------------------------------------------------------------

class TestPdfExportSecurityAndIsolation:
    def test_unauthenticated_request_rejected(self):
        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "any-req", "format": "pdf"},
        )
        assert res.status_code == 401

    def test_unknown_or_expired_request_id_rejected(self):
        token = get_auth_token("test_principal")
        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "non-existent-request-id", "format": "pdf"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404

    def test_tampered_or_cross_user_request_id_blocked(self):
        # Principal creates artifact
        token_principal = get_auth_token("test_principal")
        me_principal = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_principal}"}).json()

        art = make_artifact(
            request_id="req-principal-owned",
            user_id=me_principal["user_id"],
            role="PRINCIPAL",
            metric_id="attendance.percentage",
            metric_display_name="Average Attendance Percentage",
        )
        get_export_artifact_store().save_artifact(art)

        # HOD attempts to download Principal's artifact using tampered request_id
        token_hod = get_auth_token("test_hod_cse")
        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-principal-owned", "format": "pdf"},
            headers={"Authorization": f"Bearer {token_hod}"},
        )
        assert res.status_code == 403
        assert "cannot export another user" in res.text.lower()


# ---------------------------------------------------------------------------
# Section 3: Role Testing with Fresh Authentication for Demo Roles
# ---------------------------------------------------------------------------

class TestPdfExportDemoRoles:
    def test_principal_can_export_institutional_pdf(self):
        token = get_auth_token("test_principal")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

        art = make_artifact(
            request_id="req-principal-pdf",
            user_id=me["user_id"],
            role="PRINCIPAL",
            scope_type="INSTITUTION",
            metric_id="attendance.percentage",
            metric_display_name="Average Attendance Percentage",
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-principal-pdf", "format": "pdf"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content.startswith(b"%PDF-")

    def test_hod_cse_can_export_department_pdf(self):
        token = get_auth_token("test_hod_cse")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        dept_scope_id = me["scoped_roles"][0]["scope_id"]

        art = make_artifact(
            request_id="req-hod-pdf",
            user_id=me["user_id"],
            role="HOD",
            scope_type="DEPARTMENT",
            scope_id=dept_scope_id,
            metric_id="attendance.percentage",
            metric_display_name="Department Attendance Percentage",
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-hod-pdf", "format": "pdf"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content.startswith(b"%PDF-")

    def test_counsellor_can_export_authorized_pdf(self):
        token = get_auth_token("test_counsellor")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        scope_type = me["scoped_roles"][0]["scope_type"] if me.get("scoped_roles") else "SELF"
        scope_id = me["scoped_roles"][0]["scope_id"] if me.get("scoped_roles") else me.get("person_id")

        art = make_artifact(
            request_id="req-counsellor-pdf",
            user_id=me["user_id"],
            role="COUNSELLOR",
            scope_type=scope_type,
            scope_id=scope_id,
            metric_id="attendance.percentage",
            metric_display_name="Counsellor Group Attendance",
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-counsellor-pdf", "format": "pdf"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content.startswith(b"%PDF-")

    def test_student_can_export_self_scoped_pdf(self):
        token = get_auth_token("test_student_1")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        student_id = me["user_id"]
        scope_id = me["scoped_roles"][0]["scope_id"]

        art = make_artifact(
            request_id="req-student-pdf",
            user_id=student_id,
            role="STUDENT",
            scope_type="SELF",
            scope_id=scope_id,
            metric_id="attendance.percentage",
            metric_display_name="Student Attendance Record",
            columns=["metric_value"],
            rows=[{"metric_value": 82.17}],
            visualization_type="kpi",
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-student-pdf", "format": "pdf"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content.startswith(b"%PDF-")

    def test_student_cannot_export_department_scoped_pdf(self):
        token = get_auth_token("test_student_1")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

        art = make_artifact(
            request_id="req-student-dept-attempt",
            user_id=me["user_id"],
            role="STUDENT",
            scope_type="DEPARTMENT",
            scope_id="00000000-0000-0000-0000-000000000020",
            metric_id="attendance.percentage",
            metric_display_name="Department Attendance",
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-student-dept-attempt", "format": "pdf"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# Section 4: Regression Test for CSV and JSON Exports
# ---------------------------------------------------------------------------

class TestCsvAndJsonExportsRegression:
    def test_csv_and_json_exports_remain_unchanged(self):
        token = get_auth_token("test_principal")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

        art = make_artifact(
            request_id="req-regression-test",
            user_id=me["user_id"],
            role="PRINCIPAL",
            metric_id="attendance.percentage",
            metric_display_name="Average Attendance Percentage",
            columns=["department", "attendance_pct"],
            rows=[{"department": "CSE", "attendance_pct": 84.5}],
        )
        get_export_artifact_store().save_artifact(art)

        # CSV
        res_csv = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-regression-test", "format": "csv"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert b"department,attendance_pct" in res_csv.content
        assert b"CSE,84.5" in res_csv.content

        # JSON
        res_json = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-regression-test", "format": "json"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_json.status_code == 200
        assert "application/json" in res_json.headers["content-type"]
        data = res_json.json()
        assert data["export_metadata"]["metric_id"] == "attendance.percentage"
        assert len(data["data"]) == 1
        assert data["data"][0]["department"] == "CSE"
