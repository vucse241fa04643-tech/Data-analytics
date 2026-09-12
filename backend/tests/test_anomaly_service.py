"""Agent 63 - Phase 11: Anomaly Detection Service Unit & Security Tests

Verifies deterministic anomaly detection logic against validated QueryResults:
1. Normal numeric KPI with no anomaly
2. Threshold anomaly (attendance < 75%)
3. Target deviation anomaly (quality KPI target variance)
4. Historical anomaly (time series z-score)
5. No baseline handling
6. Insufficient historical observations (< 3 rows)
7. NULL value in result
8. NaN value in result
9. Positive infinity (+inf) in result
10. Negative infinity (-inf) in result
11. Empty result set
12. Non-numeric result set
13. Multiple dimensions (incompatible shape)
14. Category-level anomaly (single outlier category)
15. Multiple anomalous categories
16. No false anomaly from missing baseline
17. Deterministic repeated execution
18. CRITICAL SECURITY: No database access methods or connections in service
19. CRITICAL SECURITY: No SQL generation in service
20. CRITICAL SECURITY: No LLM calls (zero Groq/Gemini invocations)
"""

import math
from datetime import datetime, timezone
import pytest

from backend.app.schemas.anomaly import (
    AnomalyMethod,
    AnomalySeverity,
    AnomalyStatus,
    BaselineType,
)
from backend.app.schemas.query_result import (
    ExecutionMetadata,
    QueryResult,
    QueryResultStatus,
)
from backend.app.services.anomaly_service import (
    AnomalyDetectionService,
    get_anomaly_service,
)


def make_query_result(
    rows: list,
    columns: list,
    metric_id: str = "attendance.percentage",
    status: QueryResultStatus = QueryResultStatus.SUCCESS,
) -> QueryResult:
    """Helper to construct a validated QueryResult mock."""
    return QueryResult(
        status=status,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        metadata=ExecutionMetadata(
            execution_time_ms=5.0,
            row_count=len(rows),
            columns=columns,
            executed_at=datetime.now(timezone.utc),
            metric_id=metric_id,
        ),
    )


# 1. Normal numeric KPI with no anomaly
def test_normal_numeric_kpi_no_anomaly():
    service = get_anomaly_service()
    res = make_query_result(
        rows=[{"avg_attendance": 88.5}],
        columns=["avg_attendance"],
        metric_id="attendance.percentage",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={"filters": {"department": "CSE"}},
        metric_id="attendance.percentage",
    )
    assert assessment.status == AnomalyStatus.NO_ANOMALY
    assert assessment.detected is False
    assert assessment.severity == AnomalySeverity.NONE
    assert assessment.observed_value == 88.5
    assert assessment.baseline_value == 75.0
    assert assessment.baseline_type == BaselineType.ANALYTICAL_HEURISTIC
    assert "meets or exceeds the configured analytical detection threshold" in assessment.explanation


# 2. Threshold anomaly (attendance < 75%)
def test_threshold_anomaly_attendance():
    service = get_anomaly_service()
    res = make_query_result(
        rows=[{"avg_attendance": 68.0}],
        columns=["avg_attendance"],
        metric_id="attendance.percentage",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={"filters": {"department": "CSE"}},
        metric_id="attendance.percentage",
    )
    assert assessment.status == AnomalyStatus.ANOMALY_DETECTED
    assert assessment.detected is True
    assert assessment.method == AnomalyMethod.CONFIGURED_THRESHOLD
    assert assessment.severity == AnomalySeverity.MEDIUM  # diff is -7.0, between -5 and -15
    assert assessment.observed_value == 68.0
    assert assessment.baseline_value == 75.0
    assert assessment.baseline_type == BaselineType.ANALYTICAL_HEURISTIC
    assert assessment.deviation_value == -7.0
    assert "below the configured analytical detection threshold" in assessment.explanation
    assert "analytical heuristic and is not an official institutional policy" in assessment.explanation
    assert "institutional requirement" not in assessment.explanation.lower()
    assert "college policy" not in assessment.explanation.lower()
    assert "The result does not establish the cause." in assessment.explanation
    assert assessment.requires_review is True


# 3. Target deviation anomaly (quality KPI target variance)
def test_target_deviation_anomaly():
    service = get_anomaly_service()
    res = make_query_result(
        rows=[{"kpi_value": 72.0, "target_value": 90.0}],
        columns=["kpi_value", "target_value"],
        metric_id="quality.kpi_latest_value",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={},
        metric_id="quality.kpi_latest_value",
    )
    assert assessment.status == AnomalyStatus.ANOMALY_DETECTED
    assert assessment.detected is True
    assert assessment.method == AnomalyMethod.TARGET_DEVIATION
    assert assessment.observed_value == 72.0
    assert assessment.baseline_value == 90.0
    assert assessment.baseline_type == BaselineType.OFFICIAL_TARGET
    assert assessment.deviation_percentage == -20.0
    assert assessment.severity == AnomalySeverity.MEDIUM
    assert "official institutional target" in assessment.explanation
    assert "analytical deviation parameter" in assessment.explanation
    assert "The result does not establish the cause." in assessment.explanation


# 4. Historical anomaly (time series z-score)
def test_historical_z_score_anomaly():
    service = get_anomaly_service()
    # 2021: 82, 2022: 83, 2023: 82, 2024: 83, 2025: 64 (severe drop)
    rows = [
        {"academic_year": "2021-2022", "pass_percentage": 82.0},
        {"academic_year": "2022-2023", "pass_percentage": 83.0},
        {"academic_year": "2023-2024", "pass_percentage": 82.0},
        {"academic_year": "2024-2025", "pass_percentage": 64.0},
    ]
    res = make_query_result(
        rows=rows,
        columns=["academic_year", "pass_percentage"],
        metric_id="assessment.course_pass_percentage",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={"dimensions": ["dim.academic_year"]},
        metric_id="assessment.course_pass_percentage",
    )
    assert assessment.status == AnomalyStatus.ANOMALY_DETECTED
    assert assessment.detected is True
    assert assessment.method == AnomalyMethod.HISTORICAL_Z_SCORE
    assert assessment.severity in (AnomalySeverity.MEDIUM, AnomalySeverity.HIGH)
    assert assessment.observed_value == 64.0
    assert assessment.baseline_value == 82.33  # baseline from prior 3 years
    assert "significant statistical deviation" in assessment.explanation
    assert "The result does not establish the cause." in assessment.explanation


# 5. No baseline handling for uncalibrated metric
def test_uncalibrated_metric_no_baseline():
    service = get_anomaly_service()
    res = make_query_result(
        rows=[{"placed_count": 450}],
        columns=["placed_count"],
        metric_id="placement.placed_students_count",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={},
        metric_id="placement.placed_students_count",
    )
    assert assessment.status == AnomalyStatus.ASSESSMENT_UNAVAILABLE
    assert assessment.detected is False
    assert "No authoritative baseline or official target is present" in assessment.limitations


# 6. Insufficient historical observations (< 3 rows)
def test_insufficient_historical_observations():
    service = get_anomaly_service()
    rows = [
        {"academic_year": "2023-2024", "pass_percentage": 85.0},
        {"academic_year": "2024-2025", "pass_percentage": 70.0},
    ]
    res = make_query_result(
        rows=rows,
        columns=["academic_year", "pass_percentage"],
        metric_id="assessment.course_pass_percentage",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={"dimensions": ["dim.academic_year"]},
        metric_id="assessment.course_pass_percentage",
    )
    assert assessment.status == AnomalyStatus.ASSESSMENT_UNAVAILABLE
    assert assessment.detected is False
    assert assessment.method == AnomalyMethod.INSUFFICIENT_DATA
    assert "Insufficient historical data" in assessment.limitations


# 7. NULL value in result
def test_null_value_handling():
    service = get_anomaly_service()
    res = make_query_result(
        rows=[{"avg_attendance": None}],
        columns=["avg_attendance"],
        metric_id="attendance.percentage",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={},
        metric_id="attendance.percentage",
    )
    assert assessment.status == AnomalyStatus.ASSESSMENT_UNAVAILABLE
    assert assessment.detected is False
    assert "non-numeric" in assessment.limitations


# 8. NaN value in result
def test_nan_value_handling():
    service = get_anomaly_service()
    res = make_query_result(
        rows=[{"avg_attendance": float("nan")}],
        columns=["avg_attendance"],
        metric_id="attendance.percentage",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={},
        metric_id="attendance.percentage",
    )
    assert assessment.status == AnomalyStatus.ASSESSMENT_UNAVAILABLE
    assert assessment.detected is False
    assert "non-numeric" in assessment.limitations


# 9. Positive infinity (+inf) in result
def test_positive_infinity_handling():
    service = get_anomaly_service()
    res = make_query_result(
        rows=[{"avg_attendance": float("inf")}],
        columns=["avg_attendance"],
        metric_id="attendance.percentage",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={},
        metric_id="attendance.percentage",
    )
    assert assessment.status == AnomalyStatus.ASSESSMENT_UNAVAILABLE
    assert assessment.detected is False
    assert "non-numeric" in assessment.limitations


# 10. Negative infinity (-inf) in result
def test_negative_infinity_handling():
    service = get_anomaly_service()
    res = make_query_result(
        rows=[{"avg_attendance": float("-inf")}],
        columns=["avg_attendance"],
        metric_id="attendance.percentage",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={},
        metric_id="attendance.percentage",
    )
    assert assessment.status == AnomalyStatus.ASSESSMENT_UNAVAILABLE
    assert assessment.detected is False
    assert "non-numeric" in assessment.limitations


# 11. Empty result set
def test_empty_result_set():
    service = get_anomaly_service()
    res = make_query_result(
        rows=[],
        columns=["avg_attendance"],
        metric_id="attendance.percentage",
        status=QueryResultStatus.EMPTY,
    )
    assessment = service.assess_result(
        query_result=res,
        intent={},
        metric_id="attendance.percentage",
    )
    assert assessment.status == AnomalyStatus.ASSESSMENT_UNAVAILABLE
    assert assessment.detected is False
    assert "empty or unexecuted" in assessment.limitations


# 12. Non-numeric result set
def test_non_numeric_result_set():
    service = get_anomaly_service()
    res = make_query_result(
        rows=[{"avg_attendance": "N/A"}],
        columns=["avg_attendance"],
        metric_id="attendance.percentage",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={},
        metric_id="attendance.percentage",
    )
    assert assessment.status == AnomalyStatus.ASSESSMENT_UNAVAILABLE
    assert assessment.detected is False
    assert "non-numeric" in assessment.limitations


# 13. Multiple dimensions (incompatible shape)
def test_multiple_dimensions_incompatible_shape():
    service = get_anomaly_service()
    rows = [
        {"department": "CSE", "term": "Fall 2024", "avg_attendance": 84.0},
        {"department": "ECE", "term": "Fall 2024", "avg_attendance": 82.0},
    ]
    res = make_query_result(
        rows=rows,
        columns=["department", "term", "avg_attendance"],
        metric_id="attendance.percentage",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={"dimensions": ["dim.department", "dim.term"]},
        metric_id="attendance.percentage",
    )
    assert assessment.status == AnomalyStatus.ASSESSMENT_UNAVAILABLE
    assert assessment.detected is False
    assert "Multidimensional results with multiple grouping keys" in assessment.limitations


# 14. Category-level anomaly (single outlier category via IQR)
def test_category_level_anomaly_iqr():
    service = get_anomaly_service()
    # 5 departments: 4 normal (82, 84, 85, 83), 1 severe outlier (52)
    rows = [
        {"department": "CSE", "avg_attendance": 82.0},
        {"department": "ECE", "avg_attendance": 84.0},
        {"department": "MECH", "avg_attendance": 85.0},
        {"department": "CIVIL", "avg_attendance": 83.0},
        {"department": "BIO", "avg_attendance": 52.0},
    ]
    res = make_query_result(
        rows=rows,
        columns=["department", "avg_attendance"],
        metric_id="attendance.percentage",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={"dimensions": ["dim.department"]},
        metric_id="attendance.percentage",
    )
    assert assessment.status == AnomalyStatus.ANOMALY_DETECTED
    assert assessment.detected is True
    assert len(assessment.category_anomalies) >= 1
    outlier_names = [c.category_name for c in assessment.category_anomalies]
    assert "BIO" in outlier_names
    assert "The result does not establish the cause." in assessment.explanation


# 15. Multiple anomalous categories
def test_multiple_anomalous_categories():
    service = get_anomaly_service()
    rows = [
        {"department": "CSE", "avg_attendance": 88.0},
        {"department": "ECE", "avg_attendance": 62.0},  # below 75 benchmark
        {"department": "MECH", "avg_attendance": 65.0},  # below 75 benchmark
    ]
    res = make_query_result(
        rows=rows,
        columns=["department", "avg_attendance"],
        metric_id="attendance.percentage",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={"dimensions": ["dim.department"]},
        metric_id="attendance.percentage",
    )
    assert assessment.status == AnomalyStatus.ANOMALY_DETECTED
    assert assessment.detected is True
    assert len(assessment.category_anomalies) == 2
    anom_depts = {c.category_name for c in assessment.category_anomalies}
    assert anom_depts == {"ECE", "MECH"}


# 16. No false anomaly from missing baseline
def test_no_false_anomaly_from_missing_baseline():
    service = get_anomaly_service()
    res = make_query_result(
        rows=[{"active_strength": 1200}],
        columns=["active_strength"],
        metric_id="academics.active_student_strength",
    )
    assessment = service.assess_result(
        query_result=res,
        intent={},
        metric_id="academics.active_student_strength",
    )
    # academics.active_student_strength is not in SUPPORTED_ANOMALY_METRICS
    assert assessment.status == AnomalyStatus.ASSESSMENT_UNAVAILABLE
    assert assessment.detected is False
    assert "Metric does not support automated anomaly assessment" in assessment.limitations


# 17. Deterministic repeated execution
def test_deterministic_repeated_execution():
    service = get_anomaly_service()
    res = make_query_result(
        rows=[{"avg_attendance": 64.5}],
        columns=["avg_attendance"],
        metric_id="attendance.percentage",
    )
    run1 = service.assess_result(res, {"filters": {"department": "CSE"}}, "attendance.percentage")
    run2 = service.assess_result(res, {"filters": {"department": "CSE"}}, "attendance.percentage")
    run3 = service.assess_result(res, {"filters": {"department": "CSE"}}, "attendance.percentage")

    assert run1.status == run2.status == run3.status
    assert run1.observed_value == run2.observed_value == run3.observed_value
    assert run1.deviation_value == run2.deviation_value == run3.deviation_value
    assert run1.explanation == run2.explanation == run3.explanation


# 18. CRITICAL SECURITY: No database access methods or connections in service
def test_security_zero_database_access():
    service = get_anomaly_service()
    # Ensure service does not possess any DB connection attributes or methods
    forbidden_attrs = ["db", "database", "connection", "conn", "cursor", "execute", "psycopg", "pool"]
    for attr in forbidden_attrs:
        assert not hasattr(service, attr), f"Anomaly service violates security invariant: has '{attr}' attribute"


# 19. CRITICAL SECURITY: No SQL generation in service
def test_security_zero_sql_generation():
    service = get_anomaly_service()
    forbidden_methods = ["compile_sql", "generate_sql", "to_sql", "build_query"]
    for m in forbidden_methods:
        assert not hasattr(service, m), f"Anomaly service violates security invariant: has '{m}' method"


# 20. CRITICAL SECURITY: No LLM calls (zero Groq/Gemini invocations)
def test_security_zero_llm_invocations():
    service = get_anomaly_service()
    forbidden_clients = ["groq_client", "gemini_client", "llm_client", "openai_client"]
    for client_name in forbidden_clients:
        assert not hasattr(service, client_name), f"Anomaly service violates security invariant: has '{client_name}'"


# =========================================================================
# PHASE 11 HARDENING: BASELINE / THRESHOLD GOVERNANCE REGRESSION TESTS
# =========================================================================

# 13a. Configured analytical thresholds are NEVER described as institutional policy
def test_governance_configured_thresholds_never_described_as_institutional_policy():
    service = get_anomaly_service()
    forbidden_phrases = [
        "institutional requirement",
        "college policy",
        "official threshold",
        "official benchmark",
    ]

    # Test 1: Attendance threshold (68% < 75%)
    res_att = make_query_result(
        rows=[{"avg_attendance": 68.0}],
        columns=["avg_attendance"],
        metric_id="attendance.percentage",
    )
    assess_att = service.assess_result(res_att, {}, "attendance.percentage")
    assert assess_att.status == AnomalyStatus.ANOMALY_DETECTED
    assert assess_att.baseline_type == BaselineType.ANALYTICAL_HEURISTIC
    assert assess_att.baseline_value == 75.0
    assert "analytical heuristic and is not an official institutional policy" in assess_att.explanation
    for phrase in forbidden_phrases:
        assert phrase not in assess_att.explanation.lower(), f"Forbidden phrase '{phrase}' in attendance explanation"

    # Test 2: Pass rate threshold (52% < 60%)
    res_pass = make_query_result(
        rows=[{"course_pass_pct": 52.0}],
        columns=["course_pass_pct"],
        metric_id="assessment.course_pass_percentage",
    )
    assess_pass = service.assess_result(res_pass, {}, "assessment.course_pass_percentage")
    assert assess_pass.status == AnomalyStatus.ANOMALY_DETECTED
    assert assess_pass.baseline_type == BaselineType.ANALYTICAL_HEURISTIC
    assert assess_pass.baseline_value == 60.0
    assert "analytical heuristic and is not an official institutional policy" in assess_pass.explanation
    for phrase in forbidden_phrases:
        assert phrase not in assess_pass.explanation.lower(), f"Forbidden phrase '{phrase}' in pass rate explanation"

    # Test 3: Outcome attainment threshold (1.75 < 2.0)
    res_att_lvl = make_query_result(
        rows=[{"attainment_level": 1.75}],
        columns=["attainment_level"],
        metric_id="outcomes.co_attainment_level",
    )
    assess_att_lvl = service.assess_result(res_att_lvl, {}, "outcomes.co_attainment_level")
    assert assess_att_lvl.status == AnomalyStatus.ANOMALY_DETECTED
    assert assess_att_lvl.baseline_type == BaselineType.ANALYTICAL_HEURISTIC
    assert assess_att_lvl.baseline_value == 2.0
    assert "analytical heuristic and is not an official institutional policy" in assess_att_lvl.explanation
    for phrase in forbidden_phrases:
        assert phrase not in assess_att_lvl.explanation.lower(), f"Forbidden phrase '{phrase}' in attainment explanation"


# 13b. Authoritative target, when present in validated result, takes precedence over configured heuristics
def test_governance_authoritative_target_precedence_over_configured_heuristic():
    service = get_anomaly_service()
    # Row contains both attendance value (72.0) and an authoritative target_value (80.0)
    # Notice: 72.0 is below the 75.0 heuristic, but the validated row specifies an official target of 80.0
    res = make_query_result(
        rows=[{"avg_attendance": 72.0, "target_attendance": 80.0}],
        columns=["avg_attendance", "target_attendance"],
        metric_id="attendance.percentage",
    )
    assessment = service.assess_result(res, {}, "attendance.percentage")

    # Authoritative target MUST take precedence
    assert assessment.status == AnomalyStatus.ANOMALY_DETECTED
    assert assessment.method == AnomalyMethod.TARGET_DEVIATION
    assert assessment.baseline_type == BaselineType.OFFICIAL_TARGET
    assert assessment.baseline_value == 80.0
    assert assessment.observed_value == 72.0
    # Deviation is (72 - 80) / 80 = -10.0%
    assert assessment.deviation_percentage == -10.0
    assert "official institutional target of 80.0" in assessment.explanation
    assert "analytical deviation parameter of 5.0%" in assessment.explanation


# 13c. Missing target does NOT become a fabricated official benchmark
def test_governance_missing_target_does_not_become_fabricated_official_benchmark():
    service = get_anomaly_service()
    # Metric without configured analytical heuristic and without target column in row
    res = make_query_result(
        rows=[{"placed_count": 350}],
        columns=["placed_count"],
        metric_id="placement.placed_students_count",
    )
    assessment = service.assess_result(res, {}, "placement.placed_students_count")

    assert assessment.status == AnomalyStatus.ASSESSMENT_UNAVAILABLE
    assert assessment.detected is False
    assert assessment.method == AnomalyMethod.NONE
    assert assessment.baseline_value is None
    assert assessment.baseline_type == BaselineType.NO_BASELINE
    assert "No authoritative baseline or official target is present in the validated query result" in assessment.limitations


# 13d. Target deviation wording correctly distinguishes official target vs heuristic
def test_governance_target_deviation_wording_distinguishes_target_vs_heuristic():
    service = get_anomaly_service()
    # Sub-case 1: Below tolerance (-25%)
    res_anom = make_query_result(
        rows=[{"kpi_value": 75.0, "target_value": 100.0}],
        columns=["kpi_value", "target_value"],
        metric_id="quality.kpi_latest_value",
    )
    assess_anom = service.assess_result(res_anom, {}, "quality.kpi_latest_value")
    assert assess_anom.status == AnomalyStatus.ANOMALY_DETECTED
    assert assess_anom.baseline_type == BaselineType.OFFICIAL_TARGET
    assert "official institutional target of 100.0" in assess_anom.explanation
    assert "analytical deviation parameter of 5.0%" in assess_anom.explanation
    assert "5% institutional policy" not in assess_anom.explanation.lower()

    # Sub-case 2: Within acceptable tolerance (-2%)
    res_normal = make_query_result(
        rows=[{"kpi_value": 98.0, "target_value": 100.0}],
        columns=["kpi_value", "target_value"],
        metric_id="quality.kpi_latest_value",
    )
    assess_normal = service.assess_result(res_normal, {}, "quality.kpi_latest_value")
    assert assess_normal.status == AnomalyStatus.NO_ANOMALY
    assert assess_normal.baseline_type == BaselineType.OFFICIAL_TARGET
    assert "within the acceptable 5.0% analytical tolerance parameter of the official institutional target" in assess_normal.explanation

