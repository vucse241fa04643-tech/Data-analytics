"""Agent 63 - Phase 9: Tests for Visualization Service
Validates deterministic visualization selection (Rules A-E) and deterministic analytical explanation generation.
Ensures zero external LLM calls and strict adherence to semantic boundaries.
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from backend.app.schemas.query_result import (
    ExecutionMetadata,
    QueryResult,
    QueryResultStatus,
)
from backend.app.schemas.visualization import ChartType
from backend.app.services.visualization_service import (
    VisualizationService,
    get_visualization_service,
)


def _make_result(
    rows: list,
    columns: list,
    data_types: dict,
    metric_id: str = "academics.active_student_strength",
    status: QueryResultStatus = QueryResultStatus.SUCCESS,
    error: str = None,
    total_count: Optional[int] = None,
) -> QueryResult:
    """Helper to construct a typed QueryResult object for testing."""
    return QueryResult(
        status=status,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        metadata=ExecutionMetadata(
            execution_time_ms=12.5,
            row_count=len(rows),
            columns=columns,
            data_types=data_types,
            executed_at=datetime.now(timezone.utc),
            metric_id=metric_id,
            total_count=total_count,
        ),
        error=error,
    )


def test_rule_a_single_numeric_metric_yields_kpi():
    """RULE A: One numeric metric with one result row -> KPI card."""
    service = get_visualization_service()
    result = _make_result(
        rows=[{"avg_attendance": 80.0}],
        columns=["avg_attendance"],
        data_types={"avg_attendance": "numeric"},
        metric_id="attendance.percentage",
    )

    viz = service.select_visualization(result)
    assert viz.recommended is True
    assert viz.chart_type == ChartType.KPI
    assert viz.y_field == "avg_attendance"
    assert viz.x_field is None
    assert "Attendance" in viz.title

    explanation = service.generate_explanation(result)
    assert "80%" in explanation
    assert "Attendance" in explanation


def test_rule_a_single_row_with_dimension_filter_yields_kpi():
    """RULE A: One numeric metric with one dimension row (scoped result) -> KPI card."""
    service = get_visualization_service()
    result = _make_result(
        rows=[{"department_code": "CSE", "active_students": 42}],
        columns=["department_code", "active_students"],
        data_types={"department_code": "varchar", "active_students": "integer"},
        metric_id="academics.active_student_strength",
    )

    viz = service.select_visualization(result)
    assert viz.recommended is True
    assert viz.chart_type == ChartType.KPI
    assert viz.x_field == "department_code"
    assert viz.y_field == "active_students"

    explanation = service.generate_explanation(result)
    assert "CSE" in explanation
    assert "42" in explanation


def test_rule_b_categorical_dimension_yields_bar_chart():
    """RULE B: One categorical dimension + one numeric metric -> Bar / Horizontal Bar."""
    service = get_visualization_service()
    result = _make_result(
        rows=[
            {"department_code": "CSE", "active_students": 42},
            {"department_code": "ECE", "active_students": 38},
            {"department_code": "MECH", "active_students": 25},
        ],
        columns=["department_code", "active_students"],
        data_types={"department_code": "varchar", "active_students": "integer"},
        metric_id="academics.active_student_strength",
    )

    viz = service.select_visualization(result)
    assert viz.recommended is True
    assert viz.chart_type in (ChartType.BAR, ChartType.HORIZONTAL_BAR)
    assert viz.x_field == "department_code"
    assert viz.y_field == "active_students"

    explanation = service.generate_explanation(result)
    assert "highest for CSE at 42" in explanation
    assert "lowest for MECH at 25" in explanation


def test_rule_b_long_labels_or_many_rows_yields_horizontal_bar():
    """RULE B: Long categorical dimension labels or many rows -> Horizontal Bar."""
    service = get_visualization_service()
    result = _make_result(
        rows=[
            {"department_name": "Department of Computer Science & Engineering", "active_students": 120},
            {"department_name": "Department of Electronics & Communication Engineering", "active_students": 110},
        ],
        columns=["department_name", "active_students"],
        data_types={"department_name": "varchar", "active_students": "integer"},
        metric_id="academics.active_student_strength",
    )

    viz = service.select_visualization(result)
    assert viz.recommended is True
    assert viz.chart_type == ChartType.HORIZONTAL_BAR


def test_rule_c_temporal_dimension_yields_line_chart():
    """RULE C: Time/date dimension + numeric metric -> Line chart."""
    service = get_visualization_service()
    result = _make_result(
        rows=[
            {"academic_year": "2023-2024", "pass_percentage": 78.5},
            {"academic_year": "2024-2025", "pass_percentage": 82.0},
            {"academic_year": "2025-2026", "pass_percentage": 86.2},
        ],
        columns=["academic_year", "pass_percentage"],
        data_types={"academic_year": "varchar", "pass_percentage": "numeric"},
        metric_id="assessment.course_pass_percentage",
    )

    viz = service.select_visualization(result)
    assert viz.recommended is True
    assert viz.chart_type == ChartType.LINE
    assert viz.x_field == "academic_year"
    assert viz.y_field == "pass_percentage"

    explanation = service.generate_explanation(result)
    assert "spans from 78.5%" in explanation
    assert "86.2%" in explanation


def test_rule_d_multiple_dimensions_yields_table():
    """RULE D: Multiple dimensions or complex grouping -> Table."""
    service = get_visualization_service()
    result = _make_result(
        rows=[
            {"department_code": "CSE", "term": "Fall", "active_students": 25},
            {"department_code": "CSE", "term": "Spring", "active_students": 28},
            {"department_code": "ECE", "term": "Fall", "active_students": 20},
        ],
        columns=["department_code", "term", "active_students"],
        data_types={"department_code": "varchar", "term": "varchar", "active_students": "integer"},
        metric_id="academics.active_student_strength",
    )

    viz = service.select_visualization(result)
    assert viz.recommended is False
    assert viz.chart_type == ChartType.TABLE


def test_rule_e_empty_result_yields_none():
    """RULE E: Empty result -> chart_type = 'none', recommended = False."""
    service = get_visualization_service()
    result = _make_result(
        rows=[],
        columns=["department_code", "active_students"],
        data_types={"department_code": "varchar", "active_students": "integer"},
        metric_id="academics.active_student_strength",
        status=QueryResultStatus.EMPTY,
    )

    viz = service.select_visualization(result)
    assert viz.recommended is False
    assert viz.chart_type == ChartType.NONE

    explanation = service.generate_explanation(result)
    assert "No matching institutional records were found" in explanation


def test_rule_e_error_result_yields_safe_explanation():
    """RULE E: Error state produces safe message without leaking internals."""
    service = get_visualization_service()
    result = _make_result(
        rows=[],
        columns=[],
        data_types={},
        status=QueryResultStatus.ERROR,
        error="Internal database error",
    )

    viz = service.select_visualization(result)
    assert viz.recommended is False
    assert viz.chart_type == ChartType.NONE

    explanation = service.generate_explanation(result)
    assert "Agent 63 could not complete the query safely" in explanation
    assert "Internal database error" not in explanation


def test_null_metric_values_handled_gracefully():
    """NULL metric values are handled without errors and reflected accurately."""
    service = get_visualization_service()
    result = _make_result(
        rows=[
            {"department_code": "CSE", "avg_attendance": None},
            {"department_code": "ECE", "avg_attendance": None},
        ],
        columns=["department_code", "avg_attendance"],
        data_types={"department_code": "varchar", "avg_attendance": "numeric"},
        metric_id="attendance.percentage",
    )

    viz = service.select_visualization(result)
    assert viz.recommended is True

    explanation = service.generate_explanation(result)
    assert "NULL values" in explanation


def test_no_llm_calls_made_by_visualization_service(monkeypatch):
    """Verifies that VisualizationService makes zero external network or LLM calls."""
    # Ensure no Groq or HTTP calls can occur
    def fail_on_network(*args, **kwargs):
        raise AssertionError("Network / LLM call attempted in VisualizationService!")

    monkeypatch.setattr("urllib.request.urlopen", fail_on_network)

    service = get_visualization_service()
    result = _make_result(
        rows=[{"active_students": 100}],
        columns=["active_students"],
        data_types={"active_students": "integer"},
        metric_id="academics.active_student_strength",
    )
    viz = service.select_visualization(result)
    explanation = service.generate_explanation(result)

    assert viz.chart_type == ChartType.KPI
    assert "100" in explanation


def test_select_visualizations_section_distribution_yields_bar_and_pie():
    """Section distribution of students represents additive composition -> both BAR and PIE."""
    service = get_visualization_service()
    result = _make_result(
        rows=[
            {"section": "A", "active_student_strength": 50},
            {"section": "B", "active_student_strength": 50},
            {"section": "C", "active_student_strength": 50},
        ],
        columns=["section", "active_student_strength"],
        data_types={"section": "varchar", "active_student_strength": "integer"},
        metric_id="academics.active_student_strength",
    )
    viz_list = service.select_visualizations(result)
    types = [v.chart_type for v in viz_list]
    assert ChartType.BAR in types or ChartType.HORIZONTAL_BAR in types
    assert ChartType.PIE in types
    pie = next(v for v in viz_list if v.chart_type == ChartType.PIE)
    assert pie.title == "Section Distribution"


def test_select_visualizations_attendance_by_section_yields_bar_only():
    """Attendance percentages are independent rates (not additive) -> BAR ONLY, NO PIE."""
    service = get_visualization_service()
    result = _make_result(
        rows=[
            {"section": "A", "attendance_percentage": 82.5},
            {"section": "B", "attendance_percentage": 81.2},
            {"section": "C", "attendance_percentage": 82.3},
        ],
        columns=["section", "attendance_percentage"],
        data_types={"section": "varchar", "attendance_percentage": "numeric"},
        metric_id="attendance.percentage",
    )
    viz_list = service.select_visualizations(result)
    types = [v.chart_type for v in viz_list]
    assert ChartType.BAR in types or ChartType.HORIZONTAL_BAR in types
    assert ChartType.PIE not in types


def test_select_visualizations_placed_students_count_yields_kpi_bar_pie():
    """Placement count query produces KPI, Bar (placed vs unplaced), and Pie share with authorized total."""
    service = get_visualization_service()
    result = _make_result(
        rows=[{"metric_value": 31}],
        columns=["metric_value"],
        data_types={"metric_value": "integer"},
        metric_id="placement.placed_students_count",
        total_count=150,
    )
    viz_list = service.select_visualizations(result, intent={"filters": {"department": "CSE"}})
    types = [v.chart_type for v in viz_list]
    assert ChartType.KPI in types
    assert ChartType.BAR in types
    assert ChartType.PIE in types
    bar_chart = next(v for v in viz_list if v.chart_type == ChartType.BAR)
    assert bar_chart.data == [{"status": "Placed", "count": 31}, {"status": "Unplaced", "count": 119}]
    # Verify sum equals authorized total exactly
    assert sum(item["count"] for item in bar_chart.data) == 150


def test_select_visualizations_placed_students_count_dynamic_total():
    """Verify complement = authorized_total - category_count with arbitrary dynamic total (no hardcoded constants)."""
    service = get_visualization_service()
    custom_total = 240
    placed_count = 65
    result = _make_result(
        rows=[{"metric_value": placed_count}],
        columns=["metric_value"],
        data_types={"metric_value": "integer"},
        metric_id="placement.placed_students_count",
        total_count=custom_total,
    )
    viz_list = service.select_visualizations(result, intent={"filters": {"department": "ECE"}})
    bar_chart = next(v for v in viz_list if v.chart_type == ChartType.BAR)
    assert bar_chart.data == [
        {"status": "Placed", "count": placed_count},
        {"status": "Unplaced", "count": custom_total - placed_count},
    ]
    assert sum(item["count"] for item in bar_chart.data) == custom_total


def test_select_visualizations_without_authorized_total_omits_derived_charts():
    """When no authorized total is known, arbitrary constants are strictly avoided."""
    service = get_visualization_service()
    result = _make_result(
        rows=[{"metric_value": 31}],
        columns=["metric_value"],
        data_types={"metric_value": "integer"},
        metric_id="placement.placed_students_count",
        total_count=None,
    )
    viz_list = service.select_visualizations(result, intent={"filters": {"department": "CSE"}})
    types = [v.chart_type for v in viz_list]
    assert types == [ChartType.KPI]


def test_select_visualizations_attendance_below_75_yields_kpi_bar_pie():
    """Attendance below 75 count query produces KPI, Bar (below vs at/above), and Pie."""
    service = get_visualization_service()
    result = _make_result(
        rows=[{"metric_value": 38}],
        columns=["metric_value"],
        data_types={"metric_value": "integer"},
        metric_id="attendance.percentage",
        total_count=150,
    )
    viz_list = service.select_visualizations(
        result,
        intent={"intent_type": "THRESHOLD_QUERY", "threshold": 75, "operator": "<", "reasoning_summary": "below 75 attendance"}
    )
    types = [v.chart_type for v in viz_list]
    assert ChartType.KPI in types
    assert ChartType.BAR in types
    assert ChartType.PIE in types
    bar_chart = next(v for v in viz_list if v.chart_type == ChartType.BAR)
    assert bar_chart.data == [
        {"category": "Below 75%", "count": 38},
        {"category": "75% and Above", "count": 112},
    ]
    # Verify sum equals authorized total exactly
    assert sum(item["count"] for item in bar_chart.data) == 150


def test_select_visualizations_single_student_count_yields_kpi_only():
    """Single strength question ('How many students in my department') yields KPI only."""
    service = get_visualization_service()
    result = _make_result(
        rows=[{"metric_value": 150}],
        columns=["metric_value"],
        data_types={"metric_value": "integer"},
        metric_id="academics.active_student_strength",
    )
    viz_list = service.select_visualizations(result, intent={"reasoning_summary": "student count in department"})
    types = [v.chart_type for v in viz_list]
    assert types == [ChartType.KPI]
