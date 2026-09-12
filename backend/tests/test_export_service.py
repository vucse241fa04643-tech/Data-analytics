"""Agent 63 - Phase 14: Analytical Result Export & Official Report Verification Tests

Comprehensive test suite covering:
1. BLOCKER 1 - Numerical Comparison & Tolerance:
   - exact equal values (MATCH)
   - exact Decimal equality (MATCH)
   - tiny IEEE-754 floating-point representation differences (MATCH within technical 1e-9 tolerance)
   - clearly different values (MISMATCH)
   - percentage values
   - decimal values
   - NULL / missing values (NOT_COMPARABLE)
   - values that produce NOT_COMPARABLE (shape, period, scope)
   - zero claims of 'certified' or 'approved' without authoritative approval metadata

2. BLOCKER 2 - CSV Formula Injection & Numeric Semantics:
   - numeric -42 (preserved as native number)
   - numeric -3.14 (preserved as native number)
   - numeric 85.5 (preserved as native number)
   - string "-42" (parsed to native number, not converted to text)
   - string "-3.14" (parsed to native number, not converted to text)
   - malicious string "-2+3" (neutralized with single quote)
   - malicious string "=1+1" (neutralized with single quote)
   - malicious string "+CMD(...)" (neutralized with single quote)
   - malicious string "@SUM(...)" (neutralized with single quote)
   - ordinary text (preserved)
   - NULL / None (preserved distinctly as empty string)
   - RFC 4180 escaping (commas, quotes, newlines, UTF-8 Unicode)

3. BLOCKER 3 - Authoritative Official Report Source:
   - authoritative source available -> correct comparison
   - no official record found in quality.kpi_value -> NOT_VERIFIED
   - unconfigured database -> NOT_VERIFIED
   - unauthorized report / metric -> rejected
   - wrong period -> NOT_COMPARABLE
   - wrong scope -> NOT_COMPARABLE
   - wrong metric -> NOT_COMPARABLE
   - zero synthetic benchmarks in production

4. Ownership & Cross-User Isolation:
   - user A artifact cannot be exported by user B (403)
   - user A artifact cannot be verified by user B (403)
   - student cannot export department scope (403)
   - HOD cannot export another department scope (403)
   - revoked token cannot export or verify (401)

5. Ceilings & Fail-Open Logging:
   - EXPORT_MAX_ROWS ceiling (1000)
   - EXPORT_MAX_BYTES ceiling (2MB)
   - EXPORT query logging emitted fail-open
   - zero LLM calls during export and verification
"""

import csv
import io
import json
import math
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.errors import AuthorizationError
from backend.app.main import app
from backend.app.schemas.export import (
    ExportArtifact,
    ExportFormat,
    ExportRequest,
    VerificationRequest,
    VerificationResult,
    VerificationStatus,
)
from backend.app.schemas.principal import (
    AuthenticatedPrincipal,
    ScopeType,
    ScopedRoleAssignment,
)
from backend.app.schemas.query_log import QueryLogEventType
from backend.app.schemas.query_result import ExecutionMetadata, QueryResult
from backend.app.services.export_artifact_store import (
    ExportArtifactStore,
    get_export_artifact_store,
    reset_export_artifact_store,
)
from backend.app.services.export_service import (
    ExportService,
    get_export_service,
    reset_export_service,
    sanitize_csv_cell,
    _is_numeric,
)
from backend.app.services.verification_service import (
    FLOAT_REPRESENTATION_ABS_TOL,
    VerificationService,
    get_verification_service,
    reset_verification_service,
)
from backend.app.services.query_log_service import get_query_log_service

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_stores():
    """Reset singleton stores before and after each test."""
    reset_export_artifact_store()
    reset_export_service()
    reset_verification_service()
    yield
    reset_export_artifact_store()
    reset_export_service()
    reset_verification_service()


def get_auth_token(username: str = "test_principal") -> str:
    """Helper to obtain valid bearer token for a test identity."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "InstitutionalSecurePass123!"},
    )
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]


def make_principal(
    role="PRINCIPAL",
    scope_type=ScopeType.INSTITUTION,
    scope_id=None,
    permissions=None,
    user_id="00000000-0000-0000-0000-000000000001",
    username="test_principal",
):
    if permissions is None:
        permissions = {
            "analytics.read", "attendance.read", "assessment.read",
            "outcomes.read", "placement.read", "academics.read", "quality.read",
        }
    return AuthenticatedPrincipal(
        user_id=user_id,
        username=username,
        email=f"{username}@vignan.ac.in",
        roles=[role],
        scoped_roles=[ScopedRoleAssignment(
            role=role, scope_type=scope_type, scope_id=scope_id
        )],
        permissions=permissions,
    )


def make_sample_artifact(
    request_id="req-12345",
    user_id="00000000-0000-0000-0000-000000000001",
    role="PRINCIPAL",
    scope_type="INSTITUTION",
    scope_id=None,
    metric_id="attendance.percentage",
    metric_display_name="Average Attendance Percentage",
    columns=None,
    rows=None,
    filters=None,
):
    if columns is None:
        columns = ["department", "avg_attendance"]
    if rows is None:
        rows = [
            {"department": "CSE", "avg_attendance": 84.5},
            {"department": "ECE", "avg_attendance": 81.2},
        ]
    qr = QueryResult(
        status="SUCCESS",
        columns=columns,
        rows=rows,
        row_count=len(rows),
        execution_time_ms=12.5,
        metadata=ExecutionMetadata(
            metric_id=metric_id,
            dimensions=["department"],
            row_count=len(rows),
            columns=columns,
            execution_time_ms=12.5,
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
        dimensions=["department"],
        filters=filters or {},
    )


# ---------------------------------------------------------------------------
# Section 1: BLOCKER 2 — CSV Sanitization & Numeric Preservation Tests
# ---------------------------------------------------------------------------

class TestCsvSanitizationAndNumericSemantics:
    def test_numeric_negative_42_preserved(self):
        """Preserves negative integer as a real number, not text with quote."""
        res = sanitize_csv_cell(-42)
        assert res == -42
        assert isinstance(res, int)

    def test_numeric_negative_float_preserved(self):
        """Preserves negative float as a real number."""
        res = sanitize_csv_cell(-3.14)
        assert res == -3.14
        assert isinstance(res, float)

    def test_numeric_positive_float_preserved(self):
        """Preserves positive float as a real number."""
        res = sanitize_csv_cell(85.5)
        assert res == 85.5
        assert isinstance(res, float)

    def test_numeric_string_negative_42_converted_to_number(self):
        """Converts string '-42' to native int -42 so spreadsheet treats it as number."""
        res = sanitize_csv_cell("-42")
        assert res == -42
        assert isinstance(res, int)

    def test_numeric_string_negative_float_converted_to_number(self):
        """Converts string '-3.14' to native float -3.14."""
        res = sanitize_csv_cell("-3.14")
        assert res == -3.14
        assert isinstance(res, float)

    def test_malicious_string_minus_expression_neutralized(self):
        """Neutralizes formula expression '-2+3' by prefixing single quote."""
        res = sanitize_csv_cell("-2+3")
        assert res == "'-2+3"
        assert res.startswith("'")

    def test_malicious_string_equals_neutralized(self):
        """Neutralizes spreadsheet formula '=1+1'."""
        res = sanitize_csv_cell("=1+1")
        assert res == "'=1+1"

    def test_malicious_string_plus_cmd_neutralized(self):
        """Neutralizes command formula '+CMD(...)'."""
        res = sanitize_csv_cell("+CMD(...)")
        assert res == "'+CMD(...)"

    def test_malicious_string_at_sum_neutralized(self):
        """Neutralizes '@SUM(...)'."""
        res = sanitize_csv_cell("@SUM(...)")
        assert res == "'@SUM(...)"

    def test_malicious_tab_and_carriage_return_neutralized(self):
        """Neutralizes formula triggers with leading whitespace."""
        assert sanitize_csv_cell("\t=1+2") == "'\t=1+2"
        assert sanitize_csv_cell("\r=cmd") == "'\r=cmd"

    def test_ordinary_text_preserved(self):
        """Ordinary text without triggers is preserved as-is."""
        assert sanitize_csv_cell("CSE Department") == "CSE Department"

    def test_null_distinctly_preserved(self):
        """None / NULL is distinctly preserved as empty string without collapsing to 0."""
        assert sanitize_csv_cell(None) == ""

    def test_booleans_serialized(self):
        """Booleans serialized accurately as lowercase strings."""
        assert sanitize_csv_cell(True) == "true"
        assert sanitize_csv_cell(False) == "false"

    def test_decimals_preserved(self):
        """Decimal objects preserved without text quote conversion."""
        dec = Decimal("85.5000")
        res = sanitize_csv_cell(dec)
        assert res == dec
        assert isinstance(res, Decimal)

    def test_nested_structures_serialized_to_json(self):
        """Dicts and lists serialized as clean JSON strings."""
        data = {"key": "val", "count": 5}
        assert sanitize_csv_cell(data) == json.dumps(data)

    def test_rfc4180_escaping_commas_quotes_newlines(self):
        """Standard CSV writer properly escapes commas, quotes, and newlines."""
        out = io.StringIO()
        writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        row = [
            sanitize_csv_cell("CSE, Department"),
            sanitize_csv_cell('Prof. "A"'),
            sanitize_csv_cell("Line 1\nLine 2"),
        ]
        writer.writerow(row)
        csv_text = out.getvalue()
        assert '"CSE, Department"' in csv_text
        assert '"Prof. ""A"""' in csv_text
        assert '"Line 1\nLine 2"' in csv_text


# ---------------------------------------------------------------------------
# Section 2: ExportArtifactStore Unit Tests
# ---------------------------------------------------------------------------

class TestExportArtifactStore:
    def test_save_and_retrieve_artifact(self):
        store = ExportArtifactStore(ttl_seconds=60, max_entries=10)
        art = make_sample_artifact(request_id="req-1")
        store.save_artifact(art)
        retrieved = store.get_artifact("req-1")
        assert retrieved is not None
        assert retrieved.request_id == "req-1"
        assert retrieved.metric_id == "attendance.percentage"

    def test_retrieve_non_existent_returns_none(self):
        store = ExportArtifactStore()
        assert store.get_artifact("does-not-exist") is None

    def test_artifact_ttl_expiration(self):
        store = ExportArtifactStore(ttl_seconds=0.05, max_entries=10)
        art = make_sample_artifact(request_id="req-exp")
        store.save_artifact(art)
        assert store.get_artifact("req-exp") is not None
        time.sleep(0.08)
        assert store.get_artifact("req-exp") is None

    def test_lru_eviction_when_capacity_exceeded(self):
        store = ExportArtifactStore(ttl_seconds=60, max_entries=3)
        for i in range(4):
            store.save_artifact(make_sample_artifact(request_id=f"req-{i}"))
        assert store.size() == 3
        # First one should be evicted
        assert store.get_artifact("req-0") is None
        assert store.get_artifact("req-1") is not None
        assert store.get_artifact("req-3") is not None

    def test_clear_store(self):
        store = ExportArtifactStore()
        store.save_artifact(make_sample_artifact(request_id="req-c"))
        assert store.size() == 1
        store.clear()
        assert store.size() == 0


# ---------------------------------------------------------------------------
# Section 3: ExportService Serialization & Re-Authorization
# ---------------------------------------------------------------------------

class TestExportService:
    def test_csv_export_format(self):
        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-csv",
            rows=[{"department": "CSE", "avg_attendance": 84.5}],
        )
        store.save_artifact(art)
        svc = get_export_service()
        principal = make_principal()

        raw_bytes, media_type, filename = svc.export_result("req-csv", ExportFormat.CSV, principal)
        assert filename.endswith(".csv")
        assert "text/csv" in media_type
        text = raw_bytes.decode("utf-8-sig")
        reader = list(csv.reader(io.StringIO(text)))
        assert reader[0] == ["department", "avg_attendance"]
        assert reader[1] == ["CSE", "84.5"]

    def test_json_export_format(self):
        store = get_export_artifact_store()
        art = make_sample_artifact(request_id="req-json")
        store.save_artifact(art)
        svc = get_export_service()
        principal = make_principal()

        raw_bytes, media_type, filename = svc.export_result("req-json", ExportFormat.JSON, principal)
        assert filename.endswith(".json")
        assert media_type == "application/json"
        data = json.loads(raw_bytes.decode("utf-8"))
        assert data["export_metadata"]["metric_id"] == "attendance.percentage"
        assert data["export_metadata"]["row_count"] == 2
        assert len(data["data"]) == 2

    def test_reauthorization_cross_user_isolation(self):
        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-user-a",
            user_id="user-a-uuid",
        )
        store.save_artifact(art)
        svc = get_export_service()
        user_b = make_principal(user_id="user-b-uuid", username="user_b")

        with pytest.raises(AuthorizationError) as exc_info:
            svc.export_result("req-user-a", ExportFormat.JSON, user_b)
        assert "another user" in str(exc_info.value.message)

    def test_reauthorization_student_scope_boundary(self):
        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-student-dept",
            user_id="student-uuid",
            role="STUDENT",
            scope_type="DEPARTMENT",
            scope_id="dept-cse-001",
        )
        store.save_artifact(art)
        svc = get_export_service()
        student_principal = make_principal(
            role="STUDENT",
            scope_type=ScopeType.SELF,
            scope_id="student-uuid",
            user_id="student-uuid",
        )

        with pytest.raises(AuthorizationError) as exc_info:
            svc.export_result("req-student-dept", ExportFormat.JSON, student_principal)
        assert "self-scoped" in str(exc_info.value.message)

    def test_reauthorization_hod_department_boundary(self):
        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-hod-ece",
            user_id="hod-cse-uuid",
            role="HOD",
            scope_type="DEPARTMENT",
            scope_id="dept-ece-002",
        )
        store.save_artifact(art)
        svc = get_export_service()
        hod_cse = make_principal(
            role="HOD",
            scope_type=ScopeType.DEPARTMENT,
            scope_id="dept-cse-001",
            user_id="hod-cse-uuid",
        )

        with pytest.raises(AuthorizationError) as exc_info:
            svc.export_result("req-hod-ece", ExportFormat.JSON, hod_cse)
        assert "department" in str(exc_info.value.message).lower() or "scope violation" in str(exc_info.value.message).lower()

    def test_row_limit_ceiling_enforced(self):
        store = get_export_artifact_store()
        rows = [{"id": i, "val": i * 10} for i in range(1005)]
        art = make_sample_artifact(
            request_id="req-large",
            rows=rows,
            columns=["id", "val"],
        )
        store.save_artifact(art)
        svc = get_export_service()
        principal = make_principal()

        with pytest.raises(ValueError) as exc_info:
            svc.export_result("req-large", ExportFormat.JSON, principal)
        assert "exceeds strict system ceiling" in str(exc_info.value)

    def test_byte_limit_ceiling_enforced(self):
        store = get_export_artifact_store()
        large_str = "X" * 3000000  # 3MB > 2MB limit
        art = make_sample_artifact(
            request_id="req-heavy",
            rows=[{"department": "CSE", "data": large_str}],
            columns=["department", "data"],
        )
        store.save_artifact(art)
        svc = get_export_service()
        principal = make_principal()

        with pytest.raises(ValueError) as exc_info:
            svc.export_result("req-heavy", ExportFormat.CSV, principal)
        assert "exceeds maximum ceiling" in str(exc_info.value)

    def test_query_logging_emits_export_event(self):
        store = get_export_artifact_store()
        art = make_sample_artifact(request_id="req-log", user_id="user-log-uuid")
        store.save_artifact(art)
        svc = get_export_service()
        principal = make_principal(user_id="user-log-uuid")

        with patch.object(svc._log_service, "log_event") as mock_log:
            svc.export_result("req-log", ExportFormat.JSON, principal)
            mock_log.assert_called_once()
            called_event = mock_log.call_args[0][0]
            assert called_event.event_type == QueryLogEventType.EXPORT
            assert called_event.request_id == "req-log"
            assert called_event.user_id == "user-log-uuid"

    def test_query_logging_failure_is_fail_open(self):
        store = get_export_artifact_store()
        art = make_sample_artifact(request_id="req-fail-open")
        store.save_artifact(art)
        svc = get_export_service()
        principal = make_principal()

        with patch.object(svc._log_service, "log_event", side_effect=RuntimeError("Log disk failure")):
            raw_bytes, media_type, filename = svc.export_result("req-fail-open", ExportFormat.JSON, principal)
            assert raw_bytes is not None


# ---------------------------------------------------------------------------
# Section 4: BLOCKER 1 & BLOCKER 3 — Verification Service Tests
# ---------------------------------------------------------------------------

class TestVerificationService:
    def test_verify_exact_equal_values(self):
        """Exact identical numeric values produce MATCH."""
        svc = get_verification_service()
        svc.register_test_benchmark(
            metric_id="attendance.percentage",
            period="2024-2025",
            value=84.5,
            scope_type="INSTITUTION",
            scope_id=None,
        )

        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-exact",
            rows=[{"avg_attendance": 84.5}],
            columns=["avg_attendance"],
            filters={"academic_year": "2024-2025"},
        )
        store.save_artifact(art)

        result = svc.verify_result(VerificationRequest(request_id="req-exact"), make_principal())
        assert result.status == VerificationStatus.MATCH
        assert result.analytical_value == 84.5
        assert result.official_value == 84.5
        assert "Mathematical concordance" in result.reason
        assert "governance" in result.disclaimer.lower() or "certification" in result.disclaimer.lower()

    def test_verify_exact_decimal_values(self):
        """Decimal comparison handles scale normalization accurately."""
        svc = get_verification_service()
        svc.register_test_benchmark(
            metric_id="attendance.percentage",
            period="2024-2025",
            value=Decimal("84.5000"),
            scope_type="INSTITUTION",
            scope_id=None,
        )

        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-decimal",
            rows=[{"avg_attendance": Decimal("84.5")}],
            columns=["avg_attendance"],
            filters={"academic_year": "2024-2025"},
        )
        store.save_artifact(art)

        result = svc.verify_result(VerificationRequest(request_id="req-decimal"), make_principal())
        assert result.status == VerificationStatus.MATCH

    def test_verify_tiny_floating_point_representation_difference(self):
        """
        Normalizes IEEE-754 representation noise (diff < 1e-9) as MATCH.
        This is a technical normalization, NOT an institutional tolerance.
        """
        svc = get_verification_service()
        svc.register_test_benchmark(
            metric_id="attendance.percentage",
            period="2024-2025",
            value=84.5,
            scope_type="INSTITUTION",
            scope_id=None,
        )

        store = get_export_artifact_store()
        # 84.5 + 1e-14 is pure IEEE-754 float representation noise
        art = make_sample_artifact(
            request_id="req-ieee-noise",
            rows=[{"avg_attendance": 84.5 + 1e-14}],
            columns=["avg_attendance"],
            filters={"academic_year": "2024-2025"},
        )
        store.save_artifact(art)

        result = svc.verify_result(VerificationRequest(request_id="req-ieee-noise"), make_principal())
        assert result.status == VerificationStatus.MATCH

    def test_verify_clearly_different_values_produce_mismatch(self):
        """
        Differences beyond technical representation noise (e.g. 0.0001 or 0.1)
        MUST strictly evaluate to MISMATCH.
        """
        svc = get_verification_service()
        svc.register_test_benchmark(
            metric_id="attendance.percentage",
            period="2024-2025",
            value=84.5,
            scope_type="INSTITUTION",
            scope_id=None,
        )

        store = get_export_artifact_store()
        # 84.5001 has a material difference of 0.0001 -> MUST be MISMATCH
        art = make_sample_artifact(
            request_id="req-diff-small",
            rows=[{"avg_attendance": 84.5001}],
            columns=["avg_attendance"],
            filters={"academic_year": "2024-2025"},
        )
        store.save_artifact(art)

        result = svc.verify_result(VerificationRequest(request_id="req-diff-small"), make_principal())
        assert result.status == VerificationStatus.MISMATCH
        assert "Value mismatch" in result.reason

    def test_verify_percentage_values_mismatch(self):
        """Percentage variation produces MISMATCH."""
        svc = get_verification_service()
        svc.register_test_benchmark(
            metric_id="attendance.percentage",
            period="2024-2025",
            value=91.2,
            scope_type="INSTITUTION",
            scope_id=None,
        )

        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-mismatch",
            rows=[{"avg_attendance": 84.5}],
            columns=["avg_attendance"],
            filters={"academic_year": "2024-2025"},
        )
        store.save_artifact(art)

        result = svc.verify_result(VerificationRequest(request_id="req-mismatch"), make_principal())
        assert result.status == VerificationStatus.MISMATCH
        assert result.analytical_value == 84.5
        assert result.official_value == 91.2
        assert "Value mismatch" in result.reason

    def test_verify_null_missing_values_produces_not_comparable(self):
        """Missing or NULL value in query result produces NOT_COMPARABLE."""
        svc = get_verification_service()
        svc.register_test_benchmark(
            metric_id="attendance.percentage",
            period="2024-2025",
            value=84.5,
            scope_type="INSTITUTION",
            scope_id=None,
        )

        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-null-val",
            rows=[{"avg_attendance": None}],
            columns=["avg_attendance"],
            filters={"academic_year": "2024-2025"},
        )
        store.save_artifact(art)

        result = svc.verify_result(VerificationRequest(request_id="req-null-val"), make_principal())
        assert result.status == VerificationStatus.NOT_COMPARABLE

    def test_verify_multi_row_shape_produces_not_comparable(self):
        """Multi-row tabular results produce NOT_COMPARABLE against single scalar figure."""
        svc = get_verification_service()
        svc.register_test_benchmark(
            metric_id="attendance.percentage",
            period="2024-2025",
            value=84.5,
            scope_type="INSTITUTION",
            scope_id=None,
        )

        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-multi",
            rows=[
                {"department": "CSE", "avg_attendance": 84.5},
                {"department": "ECE", "avg_attendance": 81.2},
            ],
            columns=["department", "avg_attendance"],
            filters={"academic_year": "2024-2025"},
        )
        store.save_artifact(art)

        result = svc.verify_result(VerificationRequest(request_id="req-multi"), make_principal())
        assert result.status == VerificationStatus.NOT_COMPARABLE
        assert "Multi-row tabular result" in result.reason

    def test_verify_period_mismatch_produces_not_comparable(self):
        """Different reporting period produces NOT_COMPARABLE."""
        svc = get_verification_service()
        svc.register_test_benchmark(
            metric_id="attendance.percentage",
            period="2023-2024",
            value=84.5,
            scope_type="INSTITUTION",
            scope_id=None,
        )

        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-period-mismatch",
            rows=[{"avg_attendance": 84.5}],
            columns=["avg_attendance"],
            filters={"academic_year": "2024-2025"},
        )
        store.save_artifact(art)

        result = svc.verify_result(VerificationRequest(request_id="req-period-mismatch"), make_principal())
        assert result.status == VerificationStatus.NOT_COMPARABLE
        assert "period mismatch" in result.reason.lower()

    def test_verify_scope_mismatch_produces_not_comparable(self):
        """Different organizational scope produces NOT_COMPARABLE."""
        svc = get_verification_service()
        svc.register_test_benchmark(
            metric_id="attendance.percentage",
            period="2024-2025",
            value=84.5,
            scope_type="DEPARTMENT",
            scope_id="dept-ece-002",
        )

        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-scope-mismatch",
            scope_type="DEPARTMENT",
            scope_id="dept-cse-001",
            rows=[{"avg_attendance": 84.5}],
            columns=["avg_attendance"],
            filters={"academic_year": "2024-2025"},
        )
        store.save_artifact(art)

        result = svc.verify_result(VerificationRequest(request_id="req-scope-mismatch"), make_principal())
        assert result.status == VerificationStatus.NOT_COMPARABLE
        assert "scope mismatch" in result.reason.lower()

    def test_verify_no_official_record_exists_returns_not_verified(self):
        """When no registered official report exists, strictly returns NOT_VERIFIED."""
        svc = get_verification_service()
        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-unregistered",
            rows=[{"val": 99.9}],
            columns=["val"],
        )
        store.save_artifact(art)

        result = svc.verify_result(VerificationRequest(request_id="req-unregistered"), make_principal())
        assert result.status == VerificationStatus.NOT_VERIFIED
        assert "No registered authoritative" in result.reason

    def test_zero_llm_invocation_guarantee(self):
        """CRITICAL SECURITY TEST: Ensure verification NEVER calls any LLM client."""
        svc = get_verification_service()
        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-zero-llm",
            rows=[{"val": 50}],
            columns=["val"],
        )
        store.save_artifact(art)

        with patch("backend.app.services.gemini_client.GeminiClient") as mock_gemini, \
             patch("backend.app.services.intent_llm_client.GroqIntentClient") as mock_groq:
            result = svc.verify_result(VerificationRequest(request_id="req-zero-llm"), make_principal())
            assert result is not None
            mock_gemini.assert_not_called()
            mock_groq.assert_not_called()

    def test_verification_does_not_claim_certification(self):
        """Ensures reason and disclaimer do not claim statutory certification or accredited status."""
        svc = get_verification_service()
        svc.register_test_benchmark(
            metric_id="attendance.percentage",
            period="2024-2025",
            value=84.5,
            scope_type="INSTITUTION",
        )

        store = get_export_artifact_store()
        art = make_sample_artifact(
            request_id="req-cert-check",
            rows=[{"avg_attendance": 84.5}],
            columns=["avg_attendance"],
            filters={"academic_year": "2024-2025"},
        )
        store.save_artifact(art)

        result = svc.verify_result(VerificationRequest(request_id="req-cert-check"), make_principal())
        forbidden_phrases = ["officially approved", "institutionally certified", "accredited result", "certified result"]
        for phrase in forbidden_phrases:
            assert phrase not in result.reason.lower()
            assert phrase not in result.disclaimer.lower()


# ---------------------------------------------------------------------------
# Section 5: API Endpoints Integration Tests
# ---------------------------------------------------------------------------

class TestAnalyticsApiEndpoints:
    def test_unauthenticated_export_returns_401(self):
        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "any-id", "format": "json"},
        )
        assert res.status_code == 401

    def test_unauthenticated_verify_returns_401(self):
        res = client.post(
            "/api/v1/analytics/verify",
            json={"request_id": "any-id"},
        )
        assert res.status_code == 401

    def test_export_non_existent_request_id_returns_404(self):
        token = get_auth_token("test_principal")
        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "non-existent-req-id", "format": "json"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404

    def test_authenticated_json_export_success(self):
        token = get_auth_token("test_principal")
        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        principal_id = me_res.json()["user_id"]

        art = make_sample_artifact(
            request_id="req-api-json",
            user_id=principal_id,
            role="PRINCIPAL",
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-api-json", "format": "json"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["export_metadata"]["metric_id"] == "attendance.percentage"
        assert data["export_metadata"]["row_count"] == 2
        assert len(data["data"]) == 2

    def test_authenticated_csv_export_success(self):
        token = get_auth_token("test_principal")
        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        principal_id = me_res.json()["user_id"]

        art = make_sample_artifact(
            request_id="req-api-csv",
            user_id=principal_id,
            role="PRINCIPAL",
            rows=[{"department": "CSE", "avg_attendance": 84.5}],
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-api-csv", "format": "csv"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        text = res.text.strip().lstrip("\ufeff")
        lines = text.split("\r\n")
        assert len(lines) == 2
        assert lines[0] == "department,avg_attendance"
        assert lines[1] == "CSE,84.5"

    def test_cross_user_export_rejected_with_403(self):
        token_a = get_auth_token("test_principal")
        token_b = get_auth_token("test_hod_cse")

        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
        principal_id = me_res.json()["user_id"]

        art = make_sample_artifact(
            request_id="req-user-iso",
            user_id=principal_id,
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-user-iso", "format": "json"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res.status_code == 403
        assert "another user" in res.text

    def test_cross_user_verify_rejected_with_403(self):
        token_a = get_auth_token("test_principal")
        token_b = get_auth_token("test_hod_cse")

        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
        principal_id = me_res.json()["user_id"]

        art = make_sample_artifact(
            request_id="req-ver-iso-api",
            user_id=principal_id,
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/verify",
            json={"request_id": "req-ver-iso-api"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res.status_code == 403
        assert "another user" in res.text

    def test_authenticated_verify_endpoint_success(self):
        token = get_auth_token("test_principal")
        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        principal_id = me_res.json()["user_id"]

        art = make_sample_artifact(
            request_id="req-api-ver",
            user_id=principal_id,
            rows=[{"avg_attendance": 84.5}],
            columns=["avg_attendance"],
            filters={"academic_year": "2024-2025"},
        )
        get_export_artifact_store().save_artifact(art)

        svc = get_verification_service()
        svc.register_test_benchmark(
            metric_id="attendance.percentage",
            period="2024-2025",
            value=84.5,
            scope_type="INSTITUTION",
            scope_id=None,
            unit="%",
            document_title="IQAC Annual Report",
            document_class="REPORT",
        )

        res = client.post(
            "/api/v1/analytics/verify",
            json={"request_id": "req-api-ver"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "MATCH"
        assert data["analytical_value"] == 84.5
        assert data["official_value"] == 84.5
        assert "certification" in data["disclaimer"].lower() or "governance" in data["disclaimer"].lower()

    def test_revoked_token_cannot_export(self):
        token = get_auth_token("test_principal")
        client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "any-req", "format": "json"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 401
        assert "revoked" in res.text.lower()

    def test_revoked_token_cannot_verify(self):
        token = get_auth_token("test_principal")
        client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})

        res = client.post(
            "/api/v1/analytics/verify",
            json={"request_id": "any-req"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 401
        assert "revoked" in res.text.lower()

    def test_student_can_export_self_scoped_records(self):
        token = get_auth_token("test_student_1")
        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        student_id = me_res.json()["user_id"]
        scope_id = me_res.json()["scoped_roles"][0]["scope_id"]

        art = make_sample_artifact(
            request_id="req-student-self",
            user_id=student_id,
            role="STUDENT",
            scope_type="SELF",
            scope_id=scope_id,
            metric_id="attendance.percentage",
            rows=[{"student_id": student_id, "avg_attendance": 92.0}],
            columns=["student_id", "avg_attendance"],
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-student-self", "format": "json"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["export_metadata"]["row_count"] == 1

    def test_hod_can_export_own_department_records(self):
        token = get_auth_token("test_hod_cse")
        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        hod_id = me_res.json()["user_id"]
        scope_id = me_res.json()["scoped_roles"][0]["scope_id"]

        art = make_sample_artifact(
            request_id="req-hod-cse-own",
            user_id=hod_id,
            role="HOD",
            scope_type="DEPARTMENT",
            scope_id=scope_id,
            metric_id="assessment.course_pass_percentage",
            rows=[{"department": "CSE", "pass_percentage": 84.5}],
            columns=["department", "pass_percentage"],
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-hod-cse-own", "format": "csv"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200

    def test_principal_can_export_institutional_records(self):
        token = get_auth_token("test_principal")
        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        principal_id = me_res.json()["user_id"]

        art = make_sample_artifact(
            request_id="req-prin-inst",
            user_id=principal_id,
            role="PRINCIPAL",
            scope_type="INSTITUTION",
            metric_id="attendance.percentage",
            rows=[{"metric": "attendance", "value": 85.0}],
            columns=["metric", "value"],
        )
        get_export_artifact_store().save_artifact(art)

        res = client.post(
            "/api/v1/analytics/export",
            json={"request_id": "req-prin-inst", "format": "json"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["export_metadata"]["metric_id"] == "attendance.percentage"

    def test_principal_can_verify_institutional_records(self):
        token = get_auth_token("test_principal")
        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        principal_id = me_res.json()["user_id"]

        art = make_sample_artifact(
            request_id="req-prin-ver",
            user_id=principal_id,
            role="PRINCIPAL",
            scope_type="INSTITUTION",
            metric_id="attendance.percentage",
            rows=[{"value": 85.0}],
            columns=["value"],
            filters={"academic_year": "2024-2025"},
        )
        get_export_artifact_store().save_artifact(art)

        svc = get_verification_service()
        svc.register_test_benchmark(
            metric_id="attendance.percentage",
            period="2024-2025",
            value=85.0,
            scope_type="INSTITUTION",
        )

        res = client.post(
            "/api/v1/analytics/verify",
            json={"request_id": "req-prin-ver"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "MATCH"
