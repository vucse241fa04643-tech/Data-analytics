"""
Agent 63 - Phase 8: Result Validator Unit Tests
Tests schema validation, normalization, null preservation, NaN/Inf rejection,
and domain physical sanity checks (percentages [0, 100], counts >= 0).
"""

from datetime import date, datetime
from decimal import Decimal
import pytest

from backend.app.core.errors import ResultValidationError
from backend.app.schemas.query_result import QueryResultStatus
from backend.app.services.result_validator import ResultValidator, result_validator


class TestResultValidator:
    """Test suite for result normalization and integrity verification."""

    def test_empty_results_returns_empty_status(self):
        result = result_validator.validate_and_normalize(
            raw_columns=["id", "name"],
            raw_rows=[],
            raw_data_types={"id": "int", "name": "text"},
            metric_id="attendance.percentage",
            execution_time_ms=10.5,
        )
        assert result.status == QueryResultStatus.EMPTY
        assert result.row_count == 0
        assert result.rows == []
        assert result.columns == ["id", "name"]
        assert result.metadata.execution_time_ms == 10.5

    def test_normalizes_data_types_and_preserves_nulls(self):
        raw_rows = [
            {
                "student_id": "STU001",
                "attendance_pct": Decimal("92.50"),
                "date_observed": date(2026, 9, 1),
                "recorded_at": datetime(2026, 9, 1, 14, 30, 0),
                "remark": "  Regular attendance  ",
                "duty_leave": None,
            }
        ]
        result = result_validator.validate_and_normalize(
            raw_columns=["student_id", "attendance_pct", "date_observed", "recorded_at", "remark", "duty_leave"],
            raw_rows=raw_rows,
            raw_data_types={},
            metric_id="attendance.percentage",
            execution_time_ms=15.0,
        )

        assert result.status == QueryResultStatus.SUCCESS
        assert result.row_count == 1
        row = result.rows[0]

        # String trimmed
        assert row["remark"] == "Regular attendance"
        # Decimal to float
        assert row["attendance_pct"] == 92.50
        assert isinstance(row["attendance_pct"], float)
        # Date and Datetime to ISO-8601
        assert row["date_observed"] == "2026-09-01"
        assert row["recorded_at"] == "2026-09-01T14:30:00"
        # Null strictly preserved as None
        assert row["duty_leave"] is None

    def test_rejects_nan_value(self):
        raw_rows = [{"attendance_pct": float("nan")}]
        with pytest.raises(ResultValidationError) as exc_info:
            result_validator.validate_and_normalize(
                raw_columns=["attendance_pct"],
                raw_rows=raw_rows,
                raw_data_types={},
                metric_id="attendance.percentage",
                execution_time_ms=5.0,
            )
        assert "NaN" in str(exc_info.value)

    def test_rejects_infinity_value(self):
        raw_rows = [{"attendance_pct": float("inf")}]
        with pytest.raises(ResultValidationError) as exc_info:
            result_validator.validate_and_normalize(
                raw_columns=["attendance_pct"],
                raw_rows=raw_rows,
                raw_data_types={},
                metric_id="attendance.percentage",
                execution_time_ms=5.0,
            )
        assert "Infinity" in str(exc_info.value)

    def test_rejects_percentage_above_100(self):
        raw_rows = [{"adjusted_pct": 105.5}]
        with pytest.raises(ResultValidationError) as exc_info:
            result_validator.validate_and_normalize(
                raw_columns=["adjusted_pct"],
                raw_rows=raw_rows,
                raw_data_types={},
                metric_id="attendance.percentage",
                execution_time_ms=5.0,
            )
        assert "out of valid [0, 100] range" in str(exc_info.value)

    def test_rejects_negative_percentage(self):
        raw_rows = [{"attendance_pct": -2.0}]
        with pytest.raises(ResultValidationError) as exc_info:
            result_validator.validate_and_normalize(
                raw_columns=["attendance_pct"],
                raw_rows=raw_rows,
                raw_data_types={},
                metric_id="attendance.percentage",
                execution_time_ms=5.0,
            )
        assert "out of valid [0, 100] range" in str(exc_info.value)

    def test_rejects_negative_count_metric(self):
        raw_rows = [{"active_student_count": -5}]
        with pytest.raises(ResultValidationError) as exc_info:
            result_validator.validate_and_normalize(
                raw_columns=["active_student_count"],
                raw_rows=raw_rows,
                raw_data_types={},
                metric_id="student.active_strength",
                execution_time_ms=5.0,
            )
        assert "cannot be negative" in str(exc_info.value)

    def test_rejects_invalid_scale_1_to_3(self):
        raw_rows = [{"co_attainment": 3.8}]
        with pytest.raises(ResultValidationError) as exc_info:
            result_validator.validate_and_normalize(
                raw_columns=["co_attainment"],
                raw_rows=raw_rows,
                raw_data_types={},
                metric_id=None,
                execution_time_ms=5.0,
            )
        assert "out of valid [0, 3] range" in str(exc_info.value)
